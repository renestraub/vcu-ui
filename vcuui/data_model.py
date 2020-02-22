import time
import threading
from gps import *

from vcuui.sysinfo import SysInfo
from vcuui.mm import MM


class Model(object):
    # Singleton accessor
    instance = None

    def __init__(self):
        super().__init__()

        assert Model.instance is None
        Model.instance = self

        self.worker = ModelWorker(self)
        self.gnss = GnssWorker(self)
        self.lock = threading.Lock()
        self.data = dict()

    def setup(self):
        self.worker.setup()
        self.gnss.setup()

    def get_all(self):
        with self.lock:
            return self.data

    def publish(self, origin, value):
        # print(f'get data from {origin}')
        # print(f'values {value}')
        with self.lock:
            self.data[origin] = value

        # print(self.data)


class ModelWorker(threading.Thread):
    def __init__(self, model):
        super().__init__()

        self.model = model
        self.test = 0

    def setup(self):
        self.lock = threading.Lock()
        self.daemon = True
        self.start()

    def run(self):
        self._sysinfo()
        self._network()
        self._modem()

        cnt = 0
        while True:
            # print('worker')
            if cnt % 5 == 0:
                self._sysinfo()
            if cnt % 10 == 5:
                self._network()
            if cnt % 15 == 10:
                self._modem()

            cnt += 1
            time.sleep(1.0)

    def _sysinfo(self):
        si = SysInfo()

        ver = dict()
        ver['serial'] = si.serial()
        ver['sys'] = si.version()
        ver['bl'] = si.bootloader_version()
        self.model.publish('sys-version', ver)

        dt = dict()
        dt['date'] = si.date()
        dt['uptime'] = si.uptime()
        self.model.publish('sys-datetime', dt)

        info = dict()
        info['mem'] = si.meminfo()
        info['load'] = si.load()
        info['temp'] = si.temperature()
        info['v_in'] = si.input_voltage()
        info['v_rtc'] = si.rtc_voltage()
        self.model.publish('sys-misc', info)

    def _network(self):
        si = SysInfo()

        info = dict()
        info['bytes'] = si.ifinfo('wwan0')
        self.model.publish('net-wwan0', info)

    def _modem(self):
        info = dict()
        m = MM.modem()
        if m:  # self.test == 0:
            self.test = 1
            info['modem-id'] = str(m.id)

            state = m.state()
            access_tech = m.access_tech()
            info['state'] = state
            info['access-tech'] = access_tech

            loc_info = m.location()
            if loc_info['mcc']:
                info['location'] = loc_info

            sq = m.signal()
            info['signal-quality'] = sq

            if access_tech == 'lte':
                sig = m.signal_lte()
                info['signal-lte'] = sig
            elif access_tech == 'umts':
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

        # print(f'modem data {info}')
        self.model.publish('modem', info)


class GnssWorker(threading.Thread):
    # Singleton accessor
    # TODO: required?
    instance = None

    def __init__(self, model):
        super().__init__()

        assert GnssWorker.instance is None
        GnssWorker.instance = self

        self.model = model
        self.lock = threading.Lock()
        self.gps_session = None
        self.lon = 0
        self.lat = 0
        self.fix = 0
        self.speed = 0

    def setup(self):
        self.daemon = True
        self.start()

    def get(self):
        with self.lock:
            pos = dict()
            pos['fix'] = self.fix
            pos['lon'] = self.lon
            pos['lat'] = self.lat
            pos['speed'] = self.speed

        return pos

    def run(self):
        print("running gps thread")
        self.gps_session = gps(mode=WATCH_ENABLE|WATCH_NEWSTYLE)

        while True:
            report = self.gps_session.next()
            if report['class'] == 'TPV':
                # print(report['lon'])
                # print(report['lat'])

                with self.lock:
                    fix = report['mode']
                    if fix == 0 or fix == 1:
                        self.fix = 'No Fix'
                    elif fix == 2:
                        self.fix = '2D'
                    elif fix == 3:
                        self.fix = '3D'

                    self.lon = report['lon']
                    self.lat = report['lat']
                    if 'speed' in report:
                        self.speed = report['speed']

                pos = dict()
                pos['fix'] = self.fix
                pos['lon'] = self.lon
                pos['lat'] = self.lat
                pos['speed'] = self.speed

                self.model.publish('gnss-pos', pos)
