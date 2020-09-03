import logging
import re
import threading
import time

# TODO: Factor out NEO-M8 Code to dedicated 'driver' class
from ubxlib.server import GnssUBlox
from ubxlib.ubx_cfg_cfg import UbxCfgCfgAction
from ubxlib.ubx_cfg_esfalg import UbxCfgEsfAlg, UbxCfgEsfAlgPoll
from ubxlib.ubx_cfg_esfla import UbxCfgEsflaPoll, UbxCfgEsfla, UbxCfgEsflaSet
from ubxlib.ubx_cfg_nav5 import UbxCfgNav5, UbxCfgNav5Poll
from ubxlib.ubx_cfg_nmea import UbxCfgNmea, UbxCfgNmeaPoll
from ubxlib.ubx_cfg_prt import UbxCfgPrtPoll, UbxCfgPrtUart
from ubxlib.ubx_cfg_rst import UbxCfgRstAction
from ubxlib.ubx_esf_alg import UbxEsfAlg, UbxEsfAlgPoll
from ubxlib.ubx_esf_status import UbxEsfStatus, UbxEsfStatusPoll
from ubxlib.ubx_mon_ver import UbxMonVer, UbxMonVerPoll
from ubxlib.ubx_upd_sos import UbxUpdSosAction
from vcuui.gpsd import Gpsd

logger = logging.getLogger('vcu-ui')


class Gnss(object):
    # Singleton accessor
    instance = None

    CONNECT_TIMEOUT_IN_SEC = 30

    def __init__(self, model):
        super().__init__()

        assert Gnss.instance is None
        Gnss.instance = self

        self.model = model
        self.ubx = GnssUBlox()
        self.gnss_status = GnssStatusWorker(self, self.model)
        self.gnss_pos = GnssPositionWorker(self.model)

        # Static values, read once in setup()
        self.__msg_mon_ver = None
        self.__msg_cfg_port = None
        self.__msg_cfg_nmea = None

        # Config values, can be cached until changed by model itself
        self._clear_cached_values()

        # Live values, can be cached on page reload, see invalidate()
        self.__msg_esf_alg = None

    def setup(self):
        # Quick and dirty hack to wait until gpsd is ready
        # Timeout is 30 seconds
        logger.info('Searching gpsd service')
        gpsd = Gpsd()
        for _ in range(self.CONNECT_TIMEOUT_IN_SEC):
            ready = gpsd.setup()
            if ready:
                # gpsd is around, socket exists
                # wait until first data is seen
                res = gpsd.next(timeout=10)
                if res:
                    logger.info('gps connected')
                    break

            gpsd.cleanup()
            time.sleep(1.0)
        else:
            # No break, no connection
            logger.warning('cannot connect to gpsd, is it running?')
            return False

        gpsd.cleanup()
        gpsd = None

        self.ubx.setup()

        # Register the frame types we use
        protocols = [UbxMonVer, UbxCfgNmea, UbxCfgPrtUart, UbxCfgNav5, UbxCfgEsfAlg,
                     UbxEsfAlg, UbxEsfStatus, UbxCfgEsfla]
        for p in protocols:
            self.ubx.register_frame(p)

        # Read constant information, never reloaded
        self._mon_ver()
        self._cfg_port()
        self._cfg_nmea()

        self.gnss_status.setup()
        self.gnss_pos.setup()

        return True

    def invalidate(self):
        self.__msg_cfg_esfalg = None
        self.__msg_esf_alg = None

    def version(self):
        """
        extension_0: ROM BASE 3.01 (107888)
        extension_1: FWVER=ADR 4.21
        extension_2: PROTVER=19.20
        extension_3: MOD=NEO-M8L-0
        extension_4: FIS=0xEF4015 (100111)
        extension_5: GPS;GLO;GAL;BDS
        extension_6: SBAS;IMES;QZSS
        """
        ver = self._mon_ver()
        if ver:
            fw = ver.f.extension_1.split('=')[1]
            proto = ver.f.extension_2.split('=')[1]

            data = {
                'swVersion': Gnss.sanitize(ver.f.swVersion),
                'hwVersion': Gnss.sanitize(ver.f.hwVersion),
                'fwVersion': Gnss.sanitize(fw),
                'protocol': Gnss.sanitize(proto)
            }
        else:
            data = {
                'swVersion': 'n/a',
                'hwVersion': 'n/a',
                'fwVersion': 'n/a',
                'protocol': 'n/a'
            }
        return data

    @staticmethod
    def sanitize(string_with_zeroes):
        return string_with_zeroes.rstrip('\0x00')

    def uart_settings(self):
        cfg = self._cfg_port()
        if cfg:
            mode_str = str(cfg.get('mode')).split(': ')[1]
            data = {
                'bitrate': int(cfg.f.baudRate),
                'mode': mode_str
            }
        else:
            data = {
                'bitrate': 0,
                'mode': 'n/a'
            }
        return data

    def nmea_protocol(self):
        res = self._cfg_nmea()
        if res:
            ver_in_hex = res.f.nmeaVersion
            ver = int(ver_in_hex / 16)
            rev = int(ver_in_hex % 16)
        else:
            ver = 0
            rev = 0

        return f'{ver}.{rev}'

    def cold_start(self):
        logger.debug('executing GNSS cold start')

        msg = UbxCfgRstAction()
        msg.cold_start()
        msg.pack()
        self.ubx.send(msg)      # Will not be ACK'ed
        # TODO: Remove .pack as soon as ubxlib implements this internally

        self._clear_cached_values()

        return 'Success'

    """
    Config Save / Reset
    """
    def save_config(self):
        logger.debug('saving GNSS config')

        msg = UbxCfgCfgAction()
        msg.f.saveMask = UbxCfgCfgAction.MASK_NavConf     # To save CFG-NAV-NMEA
        self.ubx.set(msg)

        return 'Success'

    def reset_config(self):
        logger.debug('resetting GNSS config')

        msg = UbxCfgCfgAction()
        msg.f.clearMask = UbxCfgCfgAction.MASK_NavConf
        msg.f.loadMask = UbxCfgCfgAction.MASK_NavConf
        self.ubx.set(msg)

        self._clear_cached_values()

        return 'Success'

    """
    SOS - Save on Shutdown
    """
    def save_state(self):
        logger.debug('saving GNSS state (save on shutdown)')

        logger.debug('stopping receiver')
        msg = UbxCfgRstAction()
        msg.stop()
        msg.pack()
        self.ubx.send(msg)      # Will not be ACK'ed
        # TODO: Remove .pack as soon as ubxlib implements this internally

        time.sleep(0.1)

        logger.debug('saving')
        msg = UbxUpdSosAction()
        msg.f.cmd = UbxUpdSosAction.SAVE
        self.ubx.set(msg)

        logger.debug('restarting')
        msg = UbxCfgRstAction()
        msg.start()
        msg.pack()
        self.ubx.send(msg)      # Will not be ACK'ed
        # TODO: Remove .pack as soon as ubxlib implements this internally

        return 'Success'

    def clear_state(self):
        logger.debug('clearing GNSS state (save on shutdown)')

        msg = UbxUpdSosAction()
        msg.f.cmd = UbxUpdSosAction.CLEAR
        self.ubx.set(msg)

        return 'Success'

    """
    Get/set dynamic model
    """
    def dynamic_model(self):
        res = self._cfg_nav5()
        if res:
            return res.f.dynModel
        else:
            return -1

    def set_dynamic_model(self, dyn_model):
        logger.debug(f'requesting dynamic model {dyn_model}')
        assert(0 <= dyn_model <= 7)

        res = self._cfg_nav5(force=True)
        if res:
            logger.debug(f'current dynamic model {res.f.dynModel}')
            if dyn_model != res.f.dynModel:
                logger.debug('  changing')
                res.f.dynModel = dyn_model
                self.ubx.set(res)
                # TODO: Move text stuff out of this module
                res = f'Dynamic model set to {dyn_model}'
            else:
                logger.debug('  ignoring')
                res = 'Dynamic model left as is'
        else:
            res = 'Failed: GNSS not accessible.'

        return res

    """
    IMU Auto Alignment Configuration
    """
    def auto_align(self):
        res = self._cfg_esfalg()
        if res:
            return bool(res.f.bitfield & UbxCfgEsfAlg.BITFIELD_doAutoMntAlg)
        else:
            return -1

    def set_auto_align(self, align_mode):
        logger.debug(f'requesting alignment mode {align_mode}')
        res = self._cfg_esfalg(force=True)
        if res:
            current = bool(res.f.bitfield & UbxCfgEsfAlg.BITFIELD_doAutoMntAlg)
            logger.debug(f'current alignment mode {current}')
            if align_mode != (current == 1):
                logger.debug('  changing')
                if align_mode:
                    res.f.bitfield |= UbxCfgEsfAlg.BITFIELD_doAutoMntAlg
                else:
                    res.f.bitfield &= ~UbxCfgEsfAlg.BITFIELD_doAutoMntAlg

                self.ubx.set(res)
                # TODO: Move text stuff out of this module
                res = f'IMU automatic alignment set to {align_mode}'
            else:
                logger.debug('  ignoring')
                res = 'IMU automatic alignment left as is'
        else:
            res = 'Failed: GNSS not accessible.'

        return res

    def imu_cfg_angles(self):
        res = self._cfg_esfalg()
        if res:
            data = {
                'roll': res.f.roll / 100.0,
                'pitch': res.f.pitch / 100.0,
                'yaw': res.f.yaw / 100.0
            }
        else:
            data = {
                'roll': 0.0,
                'pitch': 0.0,
                'yaw': 0.0
            }
        return data

    def set_imu_cfg_angles(self, angles):
        logger.debug(f'requesting angles {angles}')
        res = self._cfg_esfalg(force=True)
        if res:
            # TODO: Add check for change
            # if align_mode != (current == 1):
            if True:
                logger.debug('  changing')

                res.f.roll = angles['roll']
                res.f.pitch = angles['pitch']
                res.f.yaw = angles['yaw']
                self.ubx.set(res)
                # TODO: Move text stuff out of this module
                res = f'IMU angles set to {angles}'
            else:
                logger.debug('  ignoring')
                res = 'IMU angles left as is'
        else:
            res = 'Failed: GNSS not accesible.'

        return res

    """
    IMU Auto Alignment State
    """
    def auto_align_state(self):
        if not self.__msg_esf_alg:
            self.__msg_esf_alg = self._esf_alg()

        if self.__msg_esf_alg:
            res = str(self.__msg_esf_alg.get('flags'))
            res = res[len('flags: '):]
        else:
            res = '<error>'
        return res

    def auto_align_angles(self):
        if not self.__msg_esf_alg:
            self.__msg_esf_alg = self._esf_alg()

        if self.__msg_esf_alg:
            roll = self.__msg_esf_alg.f.roll / 100.0
            pitch = self.__msg_esf_alg.f.pitch / 100.0
            yaw = self.__msg_esf_alg.f.yaw / 100.0
        else:
            roll, pitch, yaw = 0.0, 0.0, 0.0
        return (roll, pitch, yaw)

    """
    Lever Arm Configuration
    """
    def vrp_ant(self):
        res = self._cfg_vrp_ant()
        if res:
            data = res
        else:
            data = {
                'x': 0.0,
                'y': 0.0,
                'z': 0.0
            }
        return data

    def set_vrp_ant(self, distance):
        logger.info(f'requesting VRP-ANT distance {distance}')
        x = distance['x']
        y = distance['y']
        z = distance['z']

        set_esfla_antenna = UbxCfgEsflaSet()
        set_esfla_antenna.set(UbxCfgEsflaSet.TYPE_VRP_Antenna, x, y, z)
        res = self.ubx.set(set_esfla_antenna)
        if res:
            res = f'VRP Antenna distance set to {distance}'
        else:
            res = 'Failed: GNSS not accessible.'

        self.__msg_cfg_esfla = None     # Force re-read once we change lever arm settings
        return res

    def vrp_imu(self):
        res = self._cfg_vrp_imu()
        if res:
            data = res
        else:
            data = {
                'x': 0.0,
                'y': 0.0,
                'z': 0.0
            }
        return data

    def set_vrp_imu(self, distance):
        logger.info(f'requesting VRP-IMU distance {distance}')
        x = distance['x']
        y = distance['y']
        z = distance['z']

        set_esfla_imu = UbxCfgEsflaSet()
        set_esfla_imu.set(UbxCfgEsflaSet.TYPE_VRP_IMU, x, y, z)
        res = self.ubx.set(set_esfla_imu)
        if res:
            # TODO: Move text stuff out of this module
            res = f'VRP IMU distance set to {distance}'
        else:
            res = 'Failed: GNSS not accessible.'

        self.__msg_cfg_esfla = None     # Force re-read once we change lever arm settings
        return res

    """
    Fusion State
    """
    def esf_status(self):
        res = self._esf_status()
        if res:
            stat0_str = str(res.get('fusionMode'))
            stat1_str = str(res.get('initStatus1'))
            stat2_str = str(res.get('initStatus2'))
            data = {
                'fusion': Gnss.__extract(stat0_str, 'fusionMode'),
                'ins': Gnss.__extract(stat1_str, 'ins'),
                'imu': Gnss.__extract(stat2_str, 'imu'),
                'imu-align': Gnss.__extract(stat1_str, 'mntAlg'),
            }
        else:
            data = {
                'fusion': '-',
                'ins': '-',
                'imu': '-',
                'imu-align': '-',
            }
        return data

    """
    Modem access
    Try to cache accesses as much as possible
    """
    def _mon_ver(self):
        if not self.__msg_mon_ver:
            logger.debug('rereading __msg_mon_ver')
            self.__msg_mon_ver = self.ubx.poll(UbxMonVerPoll())

        return self.__msg_mon_ver

    def _cfg_port(self):
        if not self.__msg_cfg_port:
            logger.debug('rereading __msg_cfg_port')
            m = UbxCfgPrtPoll()
            m.f.PortId = UbxCfgPrtPoll.PORTID_Uart
            self.__msg_cfg_port = self.ubx.poll(m)

        return self.__msg_cfg_port

    def _cfg_nav5(self, force=False):
        if force or not self.__msg_cfg_nav5:
            logger.debug('rereading __msg_cfg_nav5')
            self.__msg_cfg_nav5 = self.ubx.poll(UbxCfgNav5Poll())

        return self.__msg_cfg_nav5

    def _cfg_nmea(self):
        if not self.__msg_cfg_nmea:
            logger.debug('rereading __msg_cfg_nmea')
            self.__msg_cfg_nmea = self.ubx.poll(UbxCfgNmeaPoll())

        return self.__msg_cfg_nmea

    def _cfg_esfalg(self, force=False):
        if force or not self.__msg_cfg_esfalg:
            logger.debug('rereading __msg_cfg_esfalg')
            self.__msg_cfg_esfalg = self.ubx.poll(UbxCfgEsfAlgPoll())

        return self.__msg_cfg_esfalg

    def _cfg_vrp_imu(self, force=False):
        if force or not self.__msg_cfg_esfla:
            logger.info('rereading __msg_cfg_esfla')
            self.__msg_cfg_esfla = self.ubx.poll(UbxCfgEsflaPoll())

        lever_IMU = self.__msg_cfg_esfla.lever_arm(UbxCfgEsflaSet.TYPE_VRP_IMU)
        return lever_IMU

    def _cfg_vrp_ant(self, force=False):
        if force or not self.__msg_cfg_esfla:
            logger.info('rereading __msg_cfg_esfla')
            self.__msg_cfg_esfla = self.ubx.poll(UbxCfgEsflaPoll())

        lever_antenna = self.__msg_cfg_esfla.lever_arm(UbxCfgEsflaSet.TYPE_VRP_Antenna)
        return lever_antenna

    def _esf_alg(self):
        # TODO: Cache result, only reload if required (invalidate)
        msg = UbxEsfAlgPoll()
        res = self.ubx.poll(msg)
        return res

    def _esf_status(self):
        # TODO: Cache result, only reload if required (invalidate)
        res = self.ubx.poll(UbxEsfStatusPoll())
        return res

    def _clear_cached_values(self):
        self.__msg_cfg_nav5 = None
        self.__msg_cfg_esfalg = None
        self.__msg_cfg_esfla = None

    @staticmethod
    def __extract(text, token):
        p = re.compile(token + r': ([a-z]*)')
        res = p.findall(text)
        if res:
            return res[0]
        else:
            return '-'


class GnssStatusWorker(threading.Thread):
    def __init__(self, gnss, model):
        super().__init__()

        self.gnss = gnss
        self.model = model

    def setup(self):
        self.daemon = True
        self.name = 'gnss-status'
        self.start()

    def run(self):
        versions = self.gnss.version()
        logger.info(f'versions: {versions}')
        self.model.publish('gnss', versions)

        self._gnss()

        cnt = 0
        while True:
            if cnt % 10 == 3:
                self._gnss()

            cnt += 1
            time.sleep(1.0)

    def _gnss(self):
        info = dict()

        # TODO: Code is not thread safe!! Should not call from here...
        esf_status = self.gnss.esf_status()
        info['esf-status'] = esf_status

        self.model.publish('gnss-state', info)


class GnssPositionWorker(threading.Thread):
    def __init__(self, model):
        super().__init__()

        self.model = model

        self.state = 'init'
        self.gps = None

        self.lon = 0
        self.lat = 0
        self.fix = 0
        self.speed = 0
        self.pdop = 0

    def setup(self):
        self.daemon = True
        self.name = 'gps-reader'
        self.start()

    def run(self):
        logger.info('running gps thread')
        self.state = 'init'

        while True:
            if self.state != 'connected':
                # try to connect to gpsd
                logger.debug('trying to connect to gpsd')

                self.gps = Gpsd()
                res = self.gps.setup()
                if res:
                    logger.debug('gps connected')
                    self.state = 'connected'
                else:
                    logger.warning('cannot connect to gpsd, is it running?')
                    time.sleep(2.0)

            elif self.state == 'connected':
                try:
                    report = self.gps.next()
                    if report:
                        if report['class'] == 'SKY':
                            # Remember PDOP only, will be sent on next TPV message
                            if 'pdop' in report:
                                self.pdop = report['pdop']

                        if report['class'] == 'TPV':
                            fix = report['mode']
                            if fix == 0 or fix == 1:
                                self.fix = 'No Fix'
                            elif fix == 2:
                                self.fix = '2D'
                            elif fix == 3:
                                self.fix = '3D'

                            if 'status' in report:
                                status = report['status']
                                if status == 2 and self.fix == '3D':
                                    self.fix = '3D DGPS'

                            if 'speed' in report:
                                self.speed = report['speed']

                            # Ensure we have lon/lat in report
                            # only update when present, to avoid 0/0 position messages
                            if 'lon' in report and 'lat' in report:
                                self.lon = report['lon']
                                self.lat = report['lat']

                                pos = dict()
                                pos['fix'] = self.fix
                                pos['lon'] = self.lon
                                pos['lat'] = self.lat
                                pos['speed'] = self.speed
                                pos['pdop'] = self.pdop

                                self.model.publish('gnss-pos', pos)

                except KeyError as e:
                    # For whatever reasons getting GPS data from gps
                    # daemon is very unstable.
                    # Have to handle KeyErrors in order to keep system
                    # running.
                    logger.warning('gps module KeyError')
                    logger.warning(e)

            else:
                time.sleep(0.8)
