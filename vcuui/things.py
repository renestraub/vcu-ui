"""
Store your device token in /etc/thingsboard.conf

[API]
Token = fdjkfhdskjhfds

"""
import configparser
import json
import subprocess
import threading
import time

# import pycurl -> broken
# from io import BytesIO

class Things(threading.Thread):
    # Singleton accessor
    instance = None

    def __init__(self, model):
        super().__init__()

        assert Things.instance is None
        Things.instance = self

        self.model = model
        self.state = 'init'
        self.active = False

        self.config = configparser.ConfigParser()
        self.config.read('/etc/thingsboard.conf')
        self.api_token = self.config.get('API', 'Token')
        self._data_queue = dict()

    def setup(self):
        self.daemon = True
        self.start()

    def start2(self, enable):
        if enable is True:
            if not self.active:
                self.active = True
                res = 'Started cloud logger'
            else:
                res = 'Cloud logger already running'
        else:
            print("stopping")
            if self.active:
                print("stopping")
                self.active = False
                res = 'Stopped cloud logger'
            else:
                res = 'Cloud logger not running'

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
                                next_state = 'connected'

                            # Update attributes
                            self._attributes(md)

                elif self.state == 'connected':
                    if cnt % 2 == 0:
                        self._info(md)
                        self._gnss(md)

                    self._upload_data()

                    # check for error and switch to disconnected in case of problem

                # timer handling
                if cnt % 60 == 0:
                    # update attributes every now and then
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
            self._queue('temperature', info['temp'])
            self._queue('cpu-load', info['load'][0])

#        info['mem'] = si.meminfo()
#        info['v_in'] = si.input_voltage()
#        info['v_rtc'] = si.rtc_voltage()

    def _gnss(self, md):
        if 'gnss-pos' in md:
            pos = md['gnss-pos']
            self._queue('fix', pos['fix'])
            self._queue('lon', pos['lon'])
            self._queue('lat', pos['lat'])
            self._queue('speed', pos['speed'])

    def _queue(self, key, value):
        self._data_queue[key] = value

    def _upload_data(self):
        # Send queued data
        if self._data_queue:
            self._send_data(self._data_queue)
            self._data_queue = dict()

    def _send_data(self, payload):
        # print(payload)
        as_json_string = json.dumps(payload)  # dict to json
        args = ['curl', '-v', '-d', as_json_string,
                f'https://demo.thingsboard.io/api/v1/{self.api_token}/telemetry',
                '--header', 'Content-Type:application/json']
        subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # print(res)
        # print(res.returncode)

    def _send_attribute(self, payload):
        # print(payload)
        as_json_string = json.dumps(payload)  # dict to json
        args = ['curl', '-v', '-d', as_json_string,
                f'https://demo.thingsboard.io/api/v1/{self.api_token}/attributes',
                '--header', 'Content-Type:application/json']
        subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # print(res)
        # print(res.returncode)

    """
    def _send_attribute_pycurl(self, payload):
        c = pycurl.Curl()
        c.setopt(pycurl.URL, 'https://demo.thingsboard.io/api/v1/KCeeXoOQA170t9Og11Gy/attributes')
        c.setopt(pycurl.HTTPHEADER, ['Content-Type:application/json'])
        # c.setopt(pycurl.HTTPHEADER, ['Content-Type:application/json'])
        c.setopt(pycurl.POST, 1)
        c.setopt(pycurl.TIMEOUT_MS, 3000)

        body_as_dict = {"version": "xxxx"}
        body_as_json_string = json.dumps(body_as_dict)  # dict to json
        body_as_file_object = BytesIO(body_as_json_string)
        print(body_as_file_object)
        return

        # prepare and send. See also: pycurl.READFUNCTION to pass function instead
        c.setopt(pycurl.READDATA, body_as_file_object) 
        c.setopt(pycurl.POSTFIELDSIZE, len(body_as_json_string))

        c.perform()
        c.close()
    """
