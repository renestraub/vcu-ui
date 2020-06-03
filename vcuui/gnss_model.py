import logging
import re
import threading
import time

from ubxlib.server import GnssUBlox
from ubxlib.ubx_ack import UbxAckAck
from ubxlib.ubx_cfg_esfalg import UbxCfgEsfAlg, UbxCfgEsfAlgPoll
# from ubxlib.ubx_cfg_gnss import UbxCfgGnssPoll, UbxCfgGnss
from ubxlib.ubx_cfg_nav5 import UbxCfgNav5, UbxCfgNav5Poll
from ubxlib.ubx_cfg_nmea import UbxCfgNmea, UbxCfgNmeaPoll
from ubxlib.ubx_cfg_prt import UbxCfgPrtPoll, UbxCfgPrtUart
from ubxlib.ubx_cfg_rst import UbxCfgRstAction
from ubxlib.ubx_esf_alg import UbxEsfAlg, UbxEsfAlgPoll, UbxEsfResetAlgAction
from ubxlib.ubx_esf_status import UbxEsfStatus, UbxEsfStatusPoll
# from ubxlib.ubx_upd_sos import UbxUpdSosPoll, UbxUpdSos, UbxUpdSosAction
from ubxlib.ubx_mon_ver import UbxMonVer, UbxMonVerPoll
from vcuui.gpsd import Gpsd


class Gnss(object):
    # Singleton accessor
    instance = None

    def __init__(self, model):
        super().__init__()

        FORMAT = '%(asctime)-15s %(levelname)-8s %(message)s'
        logging.basicConfig(format=FORMAT)
        logger = logging.getLogger('gnss_tool')
        logger.setLevel(logging.INFO)

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
        self.__msg_cfg_nav5 = None
        self.__msg_cfg_esfalg = None

        # Live values, can be cached on page reload, see invalidate()
        self.__msg_esf_alg = None

    def setup(self):
        self.ubx.setup()

        # Register the frame types we use
        protocols = [UbxMonVer, UbxCfgNmea, UbxCfgPrtUart, UbxCfgNav5, UbxCfgEsfAlg,
                     UbxEsfAlg, UbxEsfStatus]
        for p in protocols:
            self.ubx.register_frame(p)

        # Read constant information, never reloaded
        self._mon_ver()
        self._cfg_port()

        res = self._cfg_nmea()
        if res:
            # # Change NMEA protocol to 4.1
            # self.__msg_nmea.f.nmeaVersion = 0x41
            # self.ubx.set(self.__msg_nmea)
            pass

        self.gnss_status.setup()
        self.gnss_pos.setup()

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
                'swVersion': ver.f.swVersion,
                'hwVersion': ver.f.hwVersion,
                'fwVersion': fw,
                'protocol': proto
            }
        else:
            data = {
                'swVersion': 'n/a',
                'hwVersion': 'n/a',
                'fwVersion': 'n/a',
                'protocol': 'n/a'
            }

        return data

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
        print('Executing GNSS cold start')

        msg = UbxCfgRstAction()
        msg.cold_start()
        msg.pack()
        self.ubx.send(msg)
        # TODO: Remove .pack as soon as ubxlib implements this internally

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
        print(f'Requesting dynamic model {dyn_model}')
        assert(0 <= dyn_model <= 7)

        res = self._cfg_nav5(force=True)
        if res:
            print(f'Current dynamic model {res.f.dynModel}')
            if dyn_model != res.f.dynModel:
                print('  Changing')
                res.f.dynModel = dyn_model
                self.ubx.set(res)
                # TODO: Move text stuff out of this module
                res = f'Dynamic model set to {dyn_model}'
            else:
                print('  Ignoring')
                res = 'Dynamic model left as is'
        else:
            res = 'Failed: GNSS not accesible.'

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
        print(f'Requesting alignment mode {align_mode}')
        res = self._cfg_esfalg(force=True)
        if res:
            current = bool(res.f.bitfield & UbxCfgEsfAlg.BITFIELD_doAutoMntAlg)
            print(f'Current alignment mode {current}')
            if align_mode != (current == 1):
                print('  Changing')
                if align_mode:
                    res.f.bitfield |= UbxCfgEsfAlg.BITFIELD_doAutoMntAlg
                else:
                    res.f.bitfield &= ~UbxCfgEsfAlg.BITFIELD_doAutoMntAlg

                self.ubx.set(res)
                # TODO: Move text stuff out of this module
                res = f'IMU automatic alignment set to {align_mode}'
            else:
                print('  Ignoring')
                res = 'IMU automatic alignment left as is'
        else:
            res = 'Failed: GNSS not accesible.'

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
        print(f'Requesting angles {angles}')
        res = self._cfg_esfalg(force=True)
        if res:
            # print(f'Current alignment mode {current}')
            # if align_mode != (current == 1):
            if True:
                print('  Changing')

                res.f.roll = angles['roll']
                res.f.pitch = angles['pitch']
                res.f.yaw = angles['yaw']
                self.ubx.set(res)
                # TODO: Move text stuff out of this module
                res = f'IMU angles set to {angles}'
            else:
                print('  Ignoring')
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
            self.__msg_mon_ver = self.ubx.poll(UbxMonVerPoll())

        return self.__msg_mon_ver

    def _cfg_port(self):
        if not self.__msg_cfg_port:
            m = UbxCfgPrtPoll()
            m.f.PortId = UbxCfgPrtPoll.PORTID_Uart
            self.__msg_cfg_port = self.ubx.poll(m)

        return self.__msg_cfg_port

    def _cfg_nav5(self, force=False):
        if force or not self.__msg_cfg_nav5:
            # print('rereading __msg_cfg_nav5')
            self.__msg_cfg_nav5 = self.ubx.poll(UbxCfgNav5Poll())

        return self.__msg_cfg_nav5

    def _cfg_nmea(self):
        if not self.__msg_cfg_nmea:
            self.__msg_cfg_nmea = self.ubx.poll(UbxCfgNmeaPoll())

        return self.__msg_cfg_nmea

    def _cfg_esfalg(self, force=False):
        if force or not self.__msg_cfg_esfalg:
            # print('rereading __msg_cfg_esfalg')
            self.__msg_cfg_esfalg = self.ubx.poll(UbxCfgEsfAlgPoll())

        return self.__msg_cfg_esfalg

    def _esf_alg(self):
        # TODO: Cache result, only reload if required (invalidate)
        msg = UbxEsfAlgPoll()
        res = self.ubx.poll(msg)
        if res:
            print(res)
        return res

    def _esf_status(self):
        # TODO: Cache result, only reload if required (invalidate)
        res = self.ubx.poll(UbxEsfStatusPoll())
        # print(res)
        return res

    @staticmethod
    def __extract(text, token):
        # print(f'extract {text} {token}')
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
        self._gnss()

        cnt = 0
        while True:
            if cnt % 10 == 3:
                self._gnss()

            cnt += 1
            time.sleep(1.0)

    def _gnss(self):
        info = dict()

        esf_status = self.gnss.esf_status()
        info['esf-status'] = esf_status

        self.model.publish('gnss-state', info)


class GnssPositionWorker(threading.Thread):
    # Singleton accessor
    # TODO: required?
    instance = None

    def __init__(self, model):
        super().__init__()

        assert GnssPositionWorker.instance is None
        GnssPositionWorker.instance = self

        self.model = model

        self.state = 'init'
        self.gps_session = None
        self.lon = 0
        self.lat = 0
        self.fix = 0
        self.speed = 0
        self.pdop = 0

        self.gps = Gpsd()

    def setup(self):
        self.gps.setup()
        self.daemon = True
        self.name = 'gps-reader'
        self.start()

    def run(self):
        print('running gps thread')
        self.state = 'init'

        while True:
            if self.state != 'connected':
                # try to connect to gpsd
                try:
                    print('trying to connect to gpsd')
                    print('gps connected')
                    self.state = 'connected'

                except ConnectionRefusedError:
                    print('cannot connect to gpsd, is it running?')
                    time.sleep(2.0)

            elif self.state == 'connected':
                try:
                    report = self.gps.next()
                    if report:
                        # print('-------------------------')
                        # print(report)

                        if report['class'] == 'SKY':
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

                            if 'lon' in report and 'lat' in report:
                                self.lon = report['lon']
                                self.lat = report['lat']

                            if 'speed' in report:
                                self.speed = report['speed']

                            # Always update on TPV message
                            pos = dict()
                            pos['fix'] = self.fix
                            pos['lon'] = self.lon
                            pos['lat'] = self.lat
                            pos['speed'] = self.speed
                            pos['pdop'] = self.pdop

                            # print(f'gps data {pos}')
                            self.model.publish('gnss-pos', pos)

                except KeyError as e:
                    # For whatever reasons getting GPS data from gps
                    # daemon is very unstable.
                    # Have to handle KeyErrors in order to keep system
                    # running.
                    print('gps module KeyError')
                    print(e)

            else:
                time.sleep(0.8)
