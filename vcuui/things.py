"""
Accessor to upload data to Thingsboard

Store your device token in /etc/thingsboard.conf

[API]
Server=name:port
Token=xyz
"""
import configparser
import json
import math
import threading
import time
from io import BytesIO

import pycurl

import vcuui.data_model


class Things(threading.Thread):
    # Singleton accessor
    instance = None

    MAX_QUEUE_SIZE = 300
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
            print('ERROR: Cannot get Thingsboard config')
            print(e)
            self.has_server = False

        self._data_queue = list()

        self.lat_last_rad = 0
        self.lon_last_rad = 0

    def setup(self):
        self.daemon = True
        if self.has_server:
            self.start()

    # TODO: rename to enable or activate
    def start2(self, enable):
        if enable:
            if self.has_server:
                if not self.active:
                    self.active = True
                    res = 'Started cloud logger'
                else:
                    res = 'Cloud logger already running'
            else:
                res = 'Cannot start. No configuration present'
        else:
            print("stopping")
            if self.active:
                print("stopping")
                self.active = False
                res = 'Stopped cloud logger'
            else:
                res = 'Cloud logger not running'

        self.model.publish('cloud', self.active)

        return res

    def run(self):
        cnt = 0

        while True:
            # print("things loop")
            if self.active:
                # print("active")
                next_state = self.state
                # print("getting data")
                md = self.model.get_all()
                # print(f"have data {self.state}")

                if self.state != 'connected':
                    # Check if we are connected
                    if 'modem' in md:
                        # print("modem present")
                        m = md['modem']
                        if 'modem-id' in m:
                            # print("have modem-id")
                            if 'bearer-id' in m:
                                # print("have bearer-id")
                                cnt = 0
                                next_state = 'connected'

                elif self.state == 'connected':
                    # Gather data #

                    # Get gps update every 2nd second
                    # if cnt % 2 == 1:
                    force_update = (cnt % 60) == 0
                    self._gnss(md, force_update)

                    # Less important information
                    if cnt % 15 == 0:
                        self._info(md)

                    # Upload data #

                    # Telemetry every 30 seconds
                    if cnt % 30 == 5:
                        self._upload_data()

                    # TODO: check for error and switch to disconnected state in case of problem

                    # Attributes every now and then
                    if cnt % 120 == 5:
                        self._attributes(md)

                # state change
                if self.state != next_state:
                    print(f'Changed state from {self.state} to {next_state}')
                    self.state = next_state

                cnt += 1

            time.sleep(1.0)

    def _attributes(self, md):
        version = md['sys-version']['sys']
        serial = md['sys-version']['serial']
        attrs = {
            "serial": serial,
            "version": version,
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
            # print(data)
            self._queue_timed(data)

        if 'link' in md:
            info = md['link']
            if 'delay' in info:
                data = {
                    # TODO: rename -> wwan-delay ?
                    # TODO: format result .0f ?
                    'delay': info['delay'] * 1000.0,
                }
                self._queue_timed(data)

    def _gnss(self, md, force):
        if 'gnss-pos' in md:
            # print("have gnss data")
            pos = md['gnss-pos']
            if 'lon' in pos and 'lat' in pos:
                lon_rad = math.radians(pos['lon'])
                lat_rad = math.radians(pos['lat'])

                d = self._distance(lon_rad, lat_rad)
                # print(f'distance {d}')
                if force or d > self.GNSS_UPDATE_DISTANCE:
                    # TODO: extract only values we want
                    # print('position update')
                    self._queue_timed(pos)

                    self.lat_last_rad = lat_rad
                    self.lon_last_rad = lon_rad

    def _distance(self, lon_rad, lat_rad):
        R = 6371.0e3
        d_lat_rad = self.lat_last_rad - lat_rad
        d_lon_rad = self.lon_last_rad - lon_rad
        # print(d_lat_rad, d_lon_rad)
        # print(math.sin(d_lat_rad / 2) * math.sin(d_lat_rad / 2))
        # print(math.sin(d_lon_rad / 2) * math.sin(d_lon_rad / 2))

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
        # print(now_ms)
        data_set = {"time": now_ms, "data": data}

        num_entries = len(self._data_queue)
        if num_entries > self.MAX_QUEUE_SIZE:
            # print('queue overflow, dropping old elements')
            self._data_queue = self._data_queue[-self.MAX_QUEUE_SIZE:]

        self._data_queue.append(data_set)
        # print(len(self._data_queue2))

    def _upload_data(self):
        # Send queued data
        # TODO: more clever algorithm, sending useful sized batches every some seconds

        # Get data to send from queue
        # TODO: Limit based on size
        http_data = list()
        for entry in self._data_queue:
            data = {'ts': entry['time'], 'values': entry['data']}
            http_data.append(data)

        self._post_data('telemetry', http_data)

        # TODO: only remove from list what has been sent
        self._data_queue = list()

    def _send_attribute(self, payload):
        self._post_data('attributes', payload)

    def _post_data(self, msgtype, payload):
        assert msgtype == 'attributes' or msgtype == 'telemetry'

        c = pycurl.Curl()
        c.setopt(pycurl.URL, f'{self.api_server}/api/v1/{self.api_token}/{msgtype}')
        c.setopt(pycurl.HTTPHEADER, ['Content-Type:application/json'])
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.TIMEOUT_MS, 3000)
        # c.setopt(c.VERBOSE, True)

        body_as_json_string = json.dumps(payload)  # dict to json
        # print(body_as_json_string)
        body_as_json_bytes = body_as_json_string.encode()
        # print(body_as_json_bytes)
        body_as_file_object = BytesIO(body_as_json_bytes)
        # print(body_as_file_object)

        # prepare and send. See also: pycurl.READFUNCTION to pass function instead
        c.setopt(pycurl.READDATA, body_as_file_object)
        c.setopt(pycurl.POSTFIELDSIZE, len(body_as_json_string))

        try:
            info = dict()
            info['state'] = 'sending'
            self.model.publish('things', info)

            c.perform()
            bytes_sent = len(body_as_json_bytes)

            # print(f'Sent {bytes_sent} to {self.api_server}')

            info['state'] = 'sent'
            info['bytes'] = bytes_sent
            self.model.publish('things', info)

        except pycurl.error as e:
            print("ERROR uploading data to Thingsboard")
            print(e)
        finally:
            c.close()
