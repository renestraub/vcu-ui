import time
import threading
from ping3 import ping, verbose_ping

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
        self.gsm_connection = GsmWorker(self)
        self.lock = threading.Lock()
        self.data = dict()

        self.bearer_ip = None

    def setup(self):
        self.worker.setup()
        self.gsm_connection.setup()

    def get_all(self):
        with self.lock:
            return self.data

    def get(self, origin):
        with self.lock:
            if origin in self.data:
                return self.data[origin]

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
        self.name = 'model-worker'
        self.start()

    def run(self):
        self._sysinfo()
        self._network()
        self._modem()

        cnt = 0
        while True:
            # print('worker')
            # if cnt % 5 == 0:
            self._sysinfo()

            if cnt % 10 == 2:
                self._network()

            if cnt % 10 == 5:
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


class GsmWorker(threading.Thread):
    # Singleton accessor
    # TODO: required?
    instance = None

    def __init__(self, model):
        super().__init__()

        assert GsmWorker.instance is None
        GsmWorker.instance = self

        self.model = model
        self.state = 'init'
        self.counter = 0

    def setup(self):
        self.daemon = True
        self.name = 'gsm-worker'
        self.start()

    def run(self):
        print("running gsm thread")
        self.state = 'init'
        self.counter = 0

        while True:
            info = self.model.get('modem')
            # print(info)

            if self.state == 'init':
                # check if we have a valid bearer
                try:
                    if info and 'bearer-ip' in info:
                        print('bearer found')
                        self.state = 'connected'

                except KeyError:
                    pass

            elif self.state == 'connected':
                try:
                    if info and 'bearer-ip' not in info:
                        print('lost IP connection')
                        self.state = 'init'

                    else:
                        if self.counter % 60 == 10:
                            info = dict()
                            delay = ping('1.1.1.1', timeout=1.0)
                            if delay:
                                info['delay'] = delay
                            else:
                                delay = 0.0

                            self.model.publish('link', info)

                except KeyError:
                    pass

            self.counter += 1
            time.sleep(1.0)
