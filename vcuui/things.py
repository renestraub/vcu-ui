"""
Accessor to upload data to Thingsboard

Store your device token in /etc/thingsboard.conf

[API]
Server=name:port
Token=xyz
"""
import configparser
import json
import logging
import math
import threading
import time
from io import BytesIO

import pycurl

import vcuui.data_model
from vcuui._version import __version__ as ui_version

logger = logging.getLogger('vcu-ui')


class Things(threading.Thread):
    # Singleton accessor
    instance = None

    TELEMETRY_UPLOAD_PERIOD = 30    # Upload every 30 seconds
    ATTRIBUTE_UPLOAD_PERIOD = 120   # Upload every 120 seconds

    # New entries are dropped when this size is reached
    # Note: entries can have more than one data element
    MAX_QUEUE_SIZE = 300

    # Suppress GNSS update if movement less than this distance in meter
    GNSS_UPDATE_DISTANCE = 1.5

    def __init__(self, model):
        super().__init__()

        assert Things.instance is None
        Things.instance = self

        self.model = model
        self.state = 'init'
        self.active = False

        self.config = configparser.ConfigParser()
        try:
            self.config.read('/etc/thingsboard.conf')
            self.api_server = self.config.get('API', 'Server')
            self.api_token = self.config.get('API', 'Token')
            self.has_server = True
        except configparser.Error as e:
            logger.warning('ERROR: Cannot get Thingsboard config')
            logger.info(e)
            self.has_server = False

        self._data_queue = list()

        self.lat_last_rad = 0
        self.lon_last_rad = 0

    def setup(self):
        self.daemon = True
        if self.has_server:
            self.start()

    def enable(self, enable):
        if enable:
            if self.has_server:
                if not self.active:
                    logger.info("service starting")
                    self.active = True
                    res = 'Started cloud logger'
                else:
                    res = 'Cloud logger already running'
            else:
                res = 'Cannot start. No configuration present'
        else:
            logger.info("service stopping")
            if self.active:
                self.active = False
                res = 'Stopped cloud logger'
            else:
                res = 'Cloud logger not running'

        self.model.publish('cloud', self.active)

        return res

    def run(self):
        cnt = 0

        while True:
            if self.active:
                next_state = self.state
                md = self.model.get_all()

                if self.state != 'connected':
                    # Check if we are connected
                    if 'modem' in md:
                        m = md['modem']
                        if 'modem-id' in m:
                            if 'bearer-id' in m:
                                # logger.info('link ready, changing to connected state')
                                cnt = 0
                                next_state = 'connected'

                elif self.state == 'connected':
                    # Gather data #

                    # Force GNSS update once a minute, even if not moving
                    force_update = (cnt % 60) == 0
                    self._gnss(md, force_update)

                    # Less important information
                    if cnt % 15 == 0:
                        self._info(md)

                    # Upload data #

                    # Telemetry upload
                    if cnt % Things.TELEMETRY_UPLOAD_PERIOD == 5:
                        self._upload_telemetry()

                    # TODO: check for error and switch to disconnected state in case of problem

                    # Attributes every now and then
                    if cnt % Things.ATTRIBUTE_UPLOAD_PERIOD == 7:
                        self._attributes(md)

                # state change
                if self.state != next_state:
                    logger.info(f'changed state from {self.state} to {next_state}')
                    self.state = next_state

                cnt += 1

            time.sleep(1.0)

    def _attributes(self, md):
        os_version = md['sys-version']['sys']
        serial = md['sys-version']['serial']
        hw_ver = md['sys-version']['hw']
        uptime = md['sys-datetime']['uptime']
        attrs = {
            "serial": serial,
            "os-version": os_version,
            "ui-version": ui_version,
            "hardware": hw_ver,
            "uptime": uptime
        }
        self._send_attribute(attrs)

    def _info(self, md):
        if 'sys-misc' in md:
            info = md['sys-misc']
            data = {
                'temperature': info['temp'],
                'cpu-load': info['load'][0],
                'voltage-in': info['v_in'],
                'mem-free': info['mem'][1]
            }
            self._queue_timed(data)

        if 'link' in md:
            info = md['link']
            if 'delay' in info:
                delay_in_ms = info['delay'] * 1000.0
                data = {
                    'wwan-delay': f'{delay_in_ms:.0f}'
                }
                self._queue_timed(data)

        if 'modem' in md:
            info = md['modem']
            data = dict()

            if 'bearer-id' in info:
                id = info['bearer-id']
                data['bearer-id'] = id
                if 'bearer-uptime' in info:
                    uptime = info['bearer-uptime']
                    data['bearer-uptime'] = uptime
                self._queue_timed(data)

    def _gnss(self, md, force):
        if 'gnss-pos' in md:
            pos = md['gnss-pos']
            if 'lon' in pos and 'lat' in pos:
                lon_rad = math.radians(pos['lon'])
                lat_rad = math.radians(pos['lat'])

                d = self._distance(lon_rad, lat_rad)
                if force or d > self.GNSS_UPDATE_DISTANCE:
                    self._queue_timed(pos)

                    self.lat_last_rad = lat_rad
                    self.lon_last_rad = lon_rad

    def _distance(self, lon_rad, lat_rad):
        R = 6371.0e3
        d_lat_rad = self.lat_last_rad - lat_rad
        d_lon_rad = self.lon_last_rad - lon_rad

        a = math.sin(d_lat_rad / 2) * math.sin(d_lat_rad / 2) + \
            math.cos(lat_rad) * math.cos(self.lat_last_rad) * \
            math.sin(d_lon_rad / 2) * math.sin(d_lon_rad / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        d = R * c

        return d

    def _queue_timed(self, data):
        # Add entry to transmit queue
        # Store in map with current time
        now = time.time()
        now_ms = int(1000.0 * now)
        data_set = {"time": now_ms, "data": data}

        num_entries = len(self._data_queue)
        # logger.debug(f'num q entries {num_entries}')
        if num_entries > self.MAX_QUEUE_SIZE:
            logger.info('queue overflow, dropping old elements')
            self._data_queue = self._data_queue[-self.MAX_QUEUE_SIZE:]

        self._data_queue.append(data_set)
        # logger.debug(len(self._data_queue2))

    def _upload_telemetry(self):
        # Send queued data
        # TODO: more clever algorithm, sending useful sized batches every some seconds

        # Get data to send from queue
        # TODO: Limit based on size

        # On every upload report current queue size
        num_entries = len(self._data_queue)
        data = {'tb-qsize': num_entries}
        self._queue_timed(data)

        # Build HTTP quey string with all queue data
        http_data = list()
        for entry in self._data_queue:
            data = {'ts': entry['time'], 'values': entry['data']}
            http_data.append(data)

        res = self._post_data('telemetry', http_data)
        if res:
            self._data_queue = list()
        else:
            logger.warning('could not upload telemetry data, keeping in queue')
            logger.warning(f'{len(self._data_queue)} entries in queue')

    def _send_attribute(self, payload):
        self._post_data('attributes', payload)

    def _post_data(self, msgtype, payload):
        res = False

        assert msgtype == 'attributes' or msgtype == 'telemetry'

        c = pycurl.Curl()
        c.setopt(pycurl.URL, f'{self.api_server}/api/v1/{self.api_token}/{msgtype}')
        c.setopt(pycurl.HTTPHEADER, ['Content-Type:application/json'])
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.TIMEOUT_MS, 3000)
        # c.setopt(c.VERBOSE, True)

        body_as_json_string = json.dumps(payload)  # dict to json
        body_as_json_bytes = body_as_json_string.encode()
        body_as_file_object = BytesIO(body_as_json_bytes)

        # prepare and send. See also: pycurl.READFUNCTION to pass function instead
        c.setopt(pycurl.READDATA, body_as_file_object)
        c.setopt(pycurl.POSTFIELDSIZE, len(body_as_json_string))

        try:
            info = dict()
            info['state'] = 'sending'
            self.model.publish('things', info)

            c.perform()
            bytes_sent = len(body_as_json_bytes)
            logger.debug(f'sent {bytes_sent} to {self.api_server}')

            info['state'] = 'sent'
            info['bytes'] = bytes_sent
            self.model.publish('things', info)

            res = True

        except pycurl.error as e:
            logger.warning("failed uploading data to Thingsboard")
            logger.warning(e)
        finally:
            c.close()

        return res
