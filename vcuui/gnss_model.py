import time
import threading

from ubxlib.server import GnssUBlox
from ubxlib.ubx_ack import UbxAckAck
# from ubxlib.ubx_cfg_tp5 import UbxCfgTp5Poll, UbxCfgTp5
# from ubxlib.ubx_upd_sos import UbxUpdSosPoll, UbxUpdSos, UbxUpdSosAction
from ubxlib.ubx_mon_ver import UbxMonVerPoll, UbxMonVer
from ubxlib.ubx_cfg_nmea import UbxCfgNmeaPoll, UbxCfgNmea
from ubxlib.ubx_cfg_rst import UbxCfgRstAction
# from ubxlib.ubx_esf_status import UbxEsfStatusPoll, UbxEsfStatus
#  from ubxlib.ubx_mga_ini_time_utc import UbxMgaIniTimeUtc
# from ubxlib.ubx_cfg_gnss import UbxCfgGnssPoll, UbxCfgGnss
from ubxlib.ubx_cfg_nav5 import UbxCfgNav5Poll, UbxCfgNav5
# from ubxlib.ubx_cfg_esfalg import UbxCfgEsfAlgPoll, UbxCfgEsfAlg
# from ubxlib.ubx_esf_alg import UbxEsfAlgPoll, UbxEsfAlg, UbxEsfResetAlgAction
# from ubxlib.frame import UbxCID


class Gnss(object):
    # Singleton accessor
    instance = None

    def __init__(self, model):
        super().__init__()

        assert Gnss.instance is None
        Gnss.instance = self

        self.model = model
        self.ubx = GnssUBlox('/dev/ttyS3')
        self.gnss = GnssWorker(self.model)

        # self.data = dict()
        # TODO: Init from real values
        self.__msg_version = None
        self.__msg_nmea = None
        self.__msg_cfg_nav5 = None

    def setup(self):
        self.ubx.setup()
        self.gnss.setup()

        # Register the frame types we use
        protocols = [UbxMonVer, UbxCfgNmea, UbxCfgNav5]
        for p in protocols:
            self.ubx.register_frame(p)

        m = UbxMonVerPoll()
        self.__msg_version = self.ubx.poll(m)
        print(self.__msg_version)

        self.__msg_nmea = self.__cfg_nmea()
        print(self.__msg_nmea)
        self.__msg_nmea.f.nmeaVersion = 0x41
        self.ubx.set(self.__msg_nmea)

        self.__msg_cfg_nav5 = self.__cfg_nav5()
        print(self.__msg_cfg_nav5)

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
        # TODO: Error handling
        ver = self.__msg_version
        fw = ver.f.extension_1.split('=')[1]
        proto = ver.f.extension_2.split('=')[1]

        data = {
            'swVersion': ver.f.swVersion,
            'hwVersion': ver.f.hwVersion,
            'fwVersion': fw,
            'protocol': proto
        }
        return data

    def nmea_protocol(self):
        self.__msg_nmea = self.__cfg_nmea()
        ver_in_hex = self.__msg_nmea.f.nmeaVersion
        print(ver_in_hex)

        ver = int(ver_in_hex / 16)
        rev = int(ver_in_hex % 16)

        return f'{ver}.{rev}'

    def cold_start(self):
        print('Executing GNSS cold start')

        msg = UbxCfgRstAction()
        msg.cold_start()
        msg.pack()
        self.ubx.send(msg)
        # TODO: Remove .pack as soon as ubxlib implements this internally

        return 'Success'

    def dynamic_model(self):
        self.__msg_cfg_nav5 = self.__cfg_nav5()
        return self.__msg_cfg_nav5.f.dynModel

    def set_dynamic_model(self, dyn_model):
        print(f'Changing dynamic model to {dyn_model}')
        assert(0 <= dyn_model <= 7)

        self.__msg_cfg_nav5 = self.__cfg_nav5()
        print(f'current dyn model: {self.__msg_cfg_nav5.f.dynModel}')
        if dyn_model != self.__msg_cfg_nav5.f.dynModel:
            print('changing')
            self.__msg_cfg_nav5.f.dynModel = dyn_model
            self.ubx.set(self.__msg_cfg_nav5)
            res = 'Success'
        else:
            res = 'Ignored'

    def __cfg_nav5(self):
        msg = UbxCfgNav5Poll()
        res = self.ubx.poll(msg)
        return res

    def __cfg_nmea(self):
        msg = UbxCfgNmeaPoll()
        res = self.ubx.poll(msg)
        return res


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

