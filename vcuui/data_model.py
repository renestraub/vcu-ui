"""
vcu-ui data model

collects data from various sources and stores them in a in-memory
"database".

To enable ODB-II speed polling add the following to the vcu-ui configuration
file /etc/vcuui.conf

[OBD2]
Port = CAN port to use, e.g. can0
Speed = Bitrate to use. Either 250000 or 500000
"""

import configparser
import logging
import platform
import threading
import time

from vcuui.led import LED_BiColor
from vcuui.mm import MM
from vcuui.obd_client import OBD2
from vcuui.phy_info import PhyInfo, PhyInfo5
from vcuui.sig_quality import SignalQuality_LTE
from vcuui.sysinfo_sysfs import SysInfoSysFs
from vcuui.sysinfo_sensors import SysInfoSensors
from vcuui.vnstat import VnStat

CONF_FILE = '/etc/vcuui.conf'


logger = logging.getLogger('vcu-ui')


class Model(object):
    # Singleton accessor
    instance = None

    def __init__(self):
        super().__init__()

        assert Model.instance is None
        Model.instance = self

        self.linux_release = platform.release()

        self.worker = ModelWorker(self)
        self.lock = threading.Lock()
        self.data = dict()

        self.led_ind = LED_BiColor('/sys/class/leds/ind')
        self.led_stat = LED_BiColor('/sys/class/leds/status')
        self.cnt = 0

        self.config = configparser.ConfigParser()
        try:
            self.config.read(CONF_FILE)
            self.obd2_port = self.config.get('OBD2', 'Port')
            self.obd2_speed = int(self.config.get('OBD2', 'Speed'))
        except configparser.Error as e:
            self.obd2_port = None
            self.obd2_speed = None
            logger.warning(f'ERROR: Cannot get config from {CONF_FILE}')
            logger.info(e)

    def setup(self):
        self.led_stat.green()
        self.led_ind.green()

        self.worker.setup()

    def get_all(self):
        with self.lock:
            return self.data

    def get(self, origin):
        with self.lock:
            if origin in self.data:
                return self.data[origin]

    def publish(self, origin, value):
        """
        Report event (with data) to data model

        Safe to be called from any thread
        """
        # logger.debug(f'get data from {origin}')
        # logger.debug(f'values {value}')
        with self.lock:
            self.data[origin] = value

            if origin == 'things':
                if value['state'] == 'sending':
                    self.led_ind.yellow()
                else:
                    self.led_ind.green()

    def remove(self, origin):
        with self.lock:
            self.data.pop(origin, None)


class ModelWorker(threading.Thread):
    def __init__(self, model):
        super().__init__()

        self.model = model
        self.modem_setup_done = False

    def setup(self):
        self.lock = threading.Lock()
        self.daemon = True
        self.name = 'model-worker'

        if SysInfoSensors.sensors_present():
            logger.info('using sensors based sysinfo module')
            self.si = SysInfoSensors()
        else:
            logger.info('using sys-fs based sysinfo module')
            self.si = SysInfoSysFs()

        if self.model.linux_release.startswith("4"):
            self.broadr_phy = PhyInfo('broadr0')
        else:
            self.broadr_phy = PhyInfo5('broadr0')

        if self.model.obd2_port and self.model.obd2_speed:
            self._obd2_setup(self.model.obd2_port, self.model.obd2_speed)

        self._traffic_mon_setup()

        self.start()

    def run(self):
        cnt = 0
        while True:
            self._sysinfo()

            if cnt == 0 or cnt % 4 == 2:
                self._network()

            if cnt == 0 or cnt % 4 == 3:
                self._100base_t1()

            if cnt == 0 or cnt % 4 == 2:
                self._modem()

            if cnt == 0 or cnt % 20 == 15:
                self._disc()

            if self.model.obd2_port:
                # if cnt == 0 or cnt % 2 == 1:
                self._obd2_poll()

            if cnt == 0 or cnt % 20 == 12:
                self._traffic()

            cnt += 1
            time.sleep(1.0)

    def _sysinfo(self):
        si = self.si
        si.poll()

        ver = dict()
        ver['serial'] = si.serial()
        ver['sys'] = si.version()
        ver['bl'] = si.bootloader_version()
        ver['hw'] = si.hw_version()
        self.model.publish('sys-version', ver)

        start = dict()
        start['reason'] = si.start_reason()
        self.model.publish('sys-boot', start)

        dt = dict()
        dt['date'] = si.date()
        dt['uptime'] = si.uptime()
        self.model.publish('sys-datetime', dt)

        info = dict()
        info['mem'] = si.meminfo()
        info['load'] = si.load()
        info['temp'] = si.temperature()
        ng800_lm75 = si.temperature_lm75()
        if ng800_lm75:
            info['temp_lm75'] = ng800_lm75
        info['v_in'] = si.input_voltage()
        info['v_rtc'] = si.rtc_voltage()
        self.model.publish('sys-misc', info)

    def _disc(self):
        si = self.si

        disc = dict()
        disc['wear'] = si.emmc_wear()
        disc['part_sysroot'] = si.part_size('/sysroot')
        disc['part_data'] = si.part_size('/data')
        self.model.publish('sys-disc', disc)

    def _network(self):
        si = self.si

        info_wwan = dict()
        info_wwan['bytes'] = si.ifinfo('wwan0')
        self.model.publish('net-wwan0', info_wwan)

        info_wlan = dict()
        info_wlan['bytes'] = si.ifinfo('wlan0')
        self.model.publish('net-wlan0', info_wlan)

    def _modem_setup(self, m):
        logger.info("enabling signal query")
        if m:
            m.setup_signal_query()
            self.modem_setup_done = True
        else:
            logger.info("modem not yet ready")

    def _modem(self):
        info = dict()
        m = MM.modem()
        if m:
            if not self.modem_setup_done:
                self._modem_setup(m)

            info['modem-id'] = str(m.id)

            version = m.revision()
            info['revision'] = version

            state = m.state()
            access_tech = m.access_tech()
            info['state'] = state
            info['access-tech'] = access_tech

            loc_info = m.location()
            if loc_info['mcc']:
                info['location'] = loc_info

            sq = m.signal()
            info['signal-quality'] = sq

            # Get access tech from signal quality command as regular RAT
            # information from ModemManager is not reliable
            sig_rat = m.signal_access_tech()
            info['access-tech2'] = sig_rat

            if sig_rat == 'lte':
                sig = m.signal_lte()
                info['signal-lte'] = sig

                # Seldomly the signal fields are not defined, handle gracefully
                if sig['rsrq'] and sig['rsrp']:
                    # Compute an alternate signal quality indicator to ModemManager
                    lte_q = SignalQuality_LTE(sig['rsrq'], sig['rsrp'])
                    qual = lte_q.quality() * 100.0
                    info['signal-quality2'] = round(qual)

            elif sig_rat == 'umts':
                sig = m.signal_umts()
                info['signal-umts'] = sig

            b = m.bearer()
            if b:
                info['bearer-id'] = str(b.id)
                ut = b.uptime()
                if ut:
                    info['bearer-uptime'] = ut
                    ip = b.ip()
                    info['bearer-ip'] = ip

            s = m.sim()
            if s:
                info['sim-id'] = str(s.id)
                imsi = s.imsi()
                info['sim-imsi'] = imsi
                iccid = s.iccid()
                info['sim-iccid'] = iccid
        else:
            self.modem_setup_done = False

        self.model.publish('modem', info)

    def _obd2_setup(self, port, speed):
        logger.info(f"setting up OBD-II on port {port} at {speed} bps")
        if speed != 250000 and speed != 500000:
            speed = 500000
            logger.info(f"unsupported bitrate, using {speed}")

        self._obd2 = OBD2(port, speed)
        self._obd2.setup()

    def _obd2_poll(self):
        if self._obd2:
            info = dict()

            pid = self._obd2.speed()
            if pid:
                info['speed'] = pid.value()
            else:
                info['speed'] = 0.0

            pid = self._obd2.engine_coolant_temp()
            if pid:
                info['coolant-temp'] = pid.value()
            else:
                info['coolant-temp'] = 0.0

            self.model.publish('obd2', info)

    def _100base_t1(self):
        state = self.broadr_phy.state()
        quality = self.broadr_phy.quality()

        info = dict()
        info['state'] = state
        info['quality'] = str(quality)

        self.model.publish('phy-broadr0', info)

    def _traffic_mon_setup(self):
        logger.warning('setting up traffic monitoring')

        if VnStat.probe():
            self._vnstat = VnStat('wwan0')
            # print(f'version is {VnStat.version}')
        else:
            self._vnstat = None
            logger.info('traffic monitoring disabled')

    def _traffic(self):
        if self._vnstat:
            info = self._vnstat.get()
            if info:
                self.model.publish('traffic-wwan0', info)
