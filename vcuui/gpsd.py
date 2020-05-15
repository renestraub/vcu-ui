import json  # or `import simplejson as json` if on Python < 2.6
import logging
import queue
import re
import socket
import threading
import time

FORMAT = '%(asctime)-15s %(levelname)-8s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('gpsd_tool')
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
        # logger.debug(f'waiting {timeout}s for reponse from listener thread')
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
                        try:
                            json_strings = data.decode()
                            for s in json_strings.splitlines():
                                obj = json.loads(s)     # obj = dict of json
                                self.response_queue.put(obj)
                        except json.JSONDecodeError:
                            logger.warning('could not decode JSON data from gpsd, discarding')

                except socket.timeout:
                    pass

        except socket.error as msg:
            logger.error(msg)

        logger.debug('receiver done')
