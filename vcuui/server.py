"""
Minimal Web UI for VCU automotive gateway

Uses Tornado webserver
"""

import json
import os
import logging

import tornado.ioloop
import tornado.web
import tornado.websocket

import requests

from vcuui._version import __version__ as version
from vcuui.gnss import save_state, clear_state, start_ser2net
from vcuui.mm import MM
from vcuui.data_model import Model
from vcuui.gnss_model import Gnss

from vcuui.pageinfo import MainHandler
from vcuui.pagegnss import GnssHandler
from vcuui.tools import ping
from vcuui.things import Things


# Init section
print(f'Welcome to VCU-UI v{version}')

path = os.path.abspath(__file__)
module_path = os.path.dirname(path)
print(f'Running server from {module_path}')


class PingHandler(tornado.web.RequestHandler):
    def get(self):
        # ToDo: Use asyncio to avoid blocking server
        console = ping('1.1.1.1')
        self.write(console)


class LocationHandler(tornado.web.RequestHandler):
    def get(self):
        # ToDo: Use asyncio to avoid blocking server
        m = MM.modem()
        m.setup_location_query()
        self.write('3GPP Location query enabled')


class SignalHandler(tornado.web.RequestHandler):
    def get(self):
        # ToDo: Use asyncio to avoid blocking server
        m = MM.modem()
        m.setup_location_query()
        self.write('3GPP Location query enabled')


class ModemResetHandler(tornado.web.RequestHandler):
    def get(self):
        m = MM.modem()
        m.reset()
        self.write('Modem reset successfully')


class CloudHandler(tornado.web.RequestHandler):
    def get(self):
        enable = self.get_query_argument('enable', False)
        print(f'new state {enable}')

        things = Things.instance
        res = things.start2(enable == 'True')
        self.write(res)


class GnssColdStartHandler(tornado.web.RequestHandler):
    def get(self):
        gnss = Gnss.instance
        res = gnss.cold_start()
        self.write(res)


class GnssConfigHandler(tornado.web.RequestHandler):
    def get(self):
        # TODO: Argument check (1st level)

        dyn_model = self.get_query_argument('dyn_model', 0)
        print(f'dynamic model {dyn_model}')

        auto_align = self.get_query_argument('auto_align', 0)
        print(f'auto_align {auto_align}')

        imu_cfg_angles = self.get_query_argument('imu_cfg_angles')
        print(f'imu_cfg_angles {imu_cfg_angles}')

        angles_as_int = imu_cfg_angles.split(',')
        angles = {
            'roll': int(float(angles_as_int[0]) * 100.0),
            'pitch': int(float(angles_as_int[1]) * 100.0),
            'yaw': int(float(angles_as_int[2]) * 100.0)
        }

        gnss = Gnss.instance

        res1 = gnss.set_dynamic_model(int(dyn_model))
        res2 = gnss.set_auto_align(auto_align == "On")
        res3 = gnss.set_imu_cfg_angles(angles)
        res = res1 + '<br>' + res2 + '<br>' + res3

        self.write(res)


"""
@app.route('/do_cell_locate', method='GET')
def do_cell_locate():
    mcc = request.query['mcc']
    mnc = request.query['mnc']
    lac = request.query['lac']
    cid = request.query['cid']
    print(f'cellinfo: mcc {mcc}, mnc {mnc}, lac {lac}, cid {cid}')

    # https://opencellid.org/ajax/searchCell.php?mcc=228&mnc=1&lac=3434&cell_id=17538051
    args = {'mcc': mcc, 'mnc': mnc, 'lac': lac, 'cell_id': cid}
    r = requests.get("https://opencellid.org/ajax/searchCell.php", params=args)
    if r.text != "false":
        d = json.loads(r.text)
        lon = d["lon"]
        lat = d["lat"]

        result = f'Cell Location: {d["lon"]}/{d["lat"]}'

        # try to determine location for lon/lat with OSM reverse search
        args = {'lon': lon, 'lat': lat, 'format': 'json'}
        r = requests.get("https://nominatim.openstreetmap.org/reverse",
                         params=args)
        d = json.loads(r.text)
        if 'display_name' in d:
            print(d['display_name'])
            location = d['display_name']

            result += '</br>'
            result += f'{location}'

        result += '</br>'
        result += f'<a target="_blank" href="http://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=16">Link To OpenStreetMap</a>'

    else:
        result = 'Cell not found in opencellid database'

    return result


@app.route('/do_ser2net')
def do_ser2net():
    res = start_ser2net()
    return res


@app.route('/do_store_gnss')
def do_store_gnss():
    res = save_state()
    return res


@app.route('/do_clear_gnss')
def do_clear_gnss():
    res = clear_state()
    return res
"""

class RealtimeHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('realtime.html', 
                    title='WebSocket Realtime Test',
                    version='-'
                    )


class SimpleWebSocket(tornado.websocket.WebSocketHandler):
    connections = set()
    counter = 0
    callback = None

    def __init__(self, application, request, **kwargs):
        print(f'new SimpleWebSocket {self}')
        super().__init__(application, request, **kwargs)

    def open(self):
        print(f'opening new websocket {self}')
        SimpleWebSocket.connections.add(self)

        if not SimpleWebSocket.callback:
            SimpleWebSocket.callback = tornado.ioloop.PeriodicCallback(self.send_data, 999)
            SimpleWebSocket.callback.start()

    def send_data(self):
        SimpleWebSocket.counter += 1

        m = Model.instance
        md = m.get_all()
        if 'gnss-pos' in md:
            pos = md['gnss-pos']

        gnss = Gnss.instance
        esf_status = gnss.esf_status()
        # print(esf_status)
        
        info = {
            'time': SimpleWebSocket.counter,
            'pos': pos,
            'esf': esf_status
        }
        [client.write_message(info) for client in SimpleWebSocket.connections]

    def on_message(self, message):
        print(f'got message: {message}')
        # [client.write_message(message) for client in self.connections]

    def on_close(self):
        print('closing websocket')
        SimpleWebSocket.connections.remove(self)


def run_server(port=80):
    model = Model()
    model.setup()

    gnss = Gnss(model)
    gnss.setup()

    things = Things(model)
    things.setup()

    # Start cloud logging by default
    things.start2(True)

    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static")
    }

    app = tornado.web.Application([
        (r"/", MainHandler),
        (r"/gnss", GnssHandler),
        (r"/realtime", RealtimeHandler),
        (r"/do_ping", PingHandler),
        (r"/do_location", LocationHandler),
        (r"/do_signal", SignalHandler),
        (r"/do_modem_reset", ModemResetHandler),
        (r"/do_cloud", CloudHandler),
        (r"/do_gnss_coldstart", GnssColdStartHandler),
        (r"/do_gnss_config", GnssConfigHandler),
        (r"/websocket", SimpleWebSocket),
    ], debug=True, **settings)
    # (r"/static/(.*)", tornado.web.StaticFileHandler, {"path": "static/"}),

    logging.getLogger("tornado.access").setLevel(logging.DEBUG)
    logging.getLogger("tornado.application").setLevel(logging.DEBUG)
    logging.getLogger("tornado.general").setLevel(logging.DEBUG)

    app.listen(port)
    tornado.ioloop.IOLoop.current().start()


# Can be invoked with python3 -m vcuui.server
if __name__ == "__main__":
    run_server()
