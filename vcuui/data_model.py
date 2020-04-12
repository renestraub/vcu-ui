import time
import threading
# TODO: This module conflicts heavily with NetModule Yocto, don't use
# from gps import *
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
        self.gnss = GnssWorker(self)
        self.gsm_connection = GsmWorker(self)
        self.lock = threading.Lock()
        self.data = dict()

        self.bearer_ip = None

    def setup(self):
        self.worker.setup()
        self.gnss.setup()
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


# TODO: Move to gnss_model.py
class GnssWorker(threading.Thread):
    # Singleton accessor
    # TODO: required?
    instance = None

    def __init__(self, model):
        super().__init__()

        assert GnssWorker.instance is None
        GnssWorker.instance = self

        self.model = model

        self.state = 'init'
        self.gps_session = None
        self.lon = 0
        self.lat = 0
        self.fix = 0
        self.speed = 0

        self.gps = Gpsd('/dev/ttyS3')

    def setup(self):
        self.gps.setup()

        self.daemon = True
        self.name = 'gps-reader'
        self.start()

    def run(self):
        print("running gps thread")
        self.state = 'init'

        while True:
            if self.state != 'connected':
                # try to connect to gpsd
                try:
                    print('trying to connect to gpsd')
                    # self.gps_session = gps(mode=WATCH_ENABLE|WATCH_NEWSTYLE)
                    print('gps connected')
                    self.state = 'connected'
                    # time.sleep(2.0)

                except ConnectionRefusedError:
                    print('cannot connect to gpsd, is it running?')
                    time.sleep(2.0)

            elif self.state == 'connected':
                try:
                    # report = self.gps_session.next()
                    report = self.gps.next()
                    # TODO: Replace with positive if report:
                    if not report:
                        continue

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

                        self.lon = report['lon']
                        self.lat = report['lat']
                        if 'speed' in report:
                            self.speed = report['speed']

                        pos = dict()
                        pos['fix'] = self.fix
                        pos['lon'] = self.lon
                        pos['lat'] = self.lat
                        pos['speed'] = self.speed

                        # print(f'gps data {pos}')
                        self.model.publish('gnss-pos', pos)

                except KeyError as e:
                    # For whatever reasons getting GPS data from gps
                    # daemon is very unstable.
                    # Have to handke KeyErrors in order to keep system
                    # running
                    print('gps module KeyError')
                    print(e)

                except StopIteration:
                    print('lost connection to gpsd')
                    time.sleep(2.0)
                    self.state = 'disconnected'

            else:
                time.sleep(1.0)


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


# TODO: Temporary replacement for gps module

import queue
import socket
import json    # or `import simplejson as json` if on Python < 2.6

import logging


FORMAT = '%(asctime)-15s %(levelname)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('gnss_tool')
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)


class Gpsd(threading.Thread):
    gpsd_data_socket = ('127.0.0.1', 2947)

    def __init__(self, device_name):
        super().__init__()

        self.device_name = device_name
        self.cmd_header = f'&{self.device_name}='.encode()
        self.connect_msg = f'?WATCH={{"device":"{self.device_name}","enable":true,"json":true}}'.encode()

        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.response_queue = queue.Queue()
        self.thread_ready_event = threading.Event()
        self.thread_stop_event = threading.Event()

    def setup(self):
        # Start worker thread in daemon mode, will invoke run() method
        self.daemon = True
        self.start()

        # Wait for worker thread to become ready.
        # Without this wait we might send the command before the thread can
        # handle the response.
        logger.info('waiting for receive thread to become active')
        self.thread_ready_event.wait()

    def cleanup(self):
        logger.info('requesting thread to stop')
        self.thread_stop_event.set()

        # Wait until thread ended
        self.join(timeout=1.0)
        logger.info('thread stopped')

    def next(self, timeout=5.0):
        logger.debug(f'waiting {timeout}s for reponse from listener thread')

        try:
            response = self.response_queue.get(True, timeout)
            logger.debug(f'got response {response}')

            return response

        except queue.Empty:
            logger.warning('timeout...')

    def run(self):
        """
        Thread running method

        - receives raw data from gpsd
        - parses ubx frames, decodes them
        - if a frame is received it is put in the receive queue
        """
        # TODO: State machine with reconnect features?

        try:
            logger.info('connecting to gpsd')
            self.listen_sock.connect(self.gpsd_data_socket)
        except socket.error as msg:
            logger.error(msg)
            # TODO: Error handling

        try:
            logger.debug('starting raw listener on gpsd')
            self.listen_sock.send(self.connect_msg)
            self.listen_sock.settimeout(0.25)

            logger.debug('receiver ready')
            self.thread_ready_event.set()

            while not self.thread_stop_event.is_set():
                try:
                    data = self.listen_sock.recv(8192)
                    if data:
                        json_strings = data.decode()
                        for s in json_strings.splitlines():
                            obj = json.loads(s)     # obj = dict of json
                            self.response_queue.put(obj)

                except socket.timeout:
                    pass

        except socket.error as msg:
            logger.error(msg)

        logger.debug('receiver done')
