"""
Minimal Web UI for VCU automotive gateway

Uses Tornado webserver
"""

import json
import logging
import os

import requests
import tornado.ioloop
import tornado.web
import tornado.websocket

from vcuui._version import __version__ as version
from vcuui.data_model import Model
from vcuui.wwan_model import Wwan
from vcuui.gnss_model import Gnss
from vcuui.mm import MM
from vcuui.pagegnss import GnssHandler
from vcuui.realtime import RealtimeHandler, RealtimeWebSocket
from vcuui.pageinfo import MainHandler
from vcuui.things import Things
from vcuui.tools import ping


FORMAT = '%(asctime)-15s %(levelname)-8s %(module)-12s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('vcu-ui')
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)


# Init section
logger.info(f'welcome to VCU-UI v{version}')

path = os.path.abspath(__file__)
module_path = os.path.dirname(path)
logger.info(f'running server from {module_path}')


class LocationHandler(tornado.web.RequestHandler):
    def get(self):
        m = MM.modem()
        if m:
            m.setup_location_query()
            self.write('3GPP location query enabled')
        else:
            self.write('No modem found')


class SignalHandler(tornado.web.RequestHandler):
    def get(self):
        logger.info('enabling modem signal quality measurements')
        m = MM.modem()
        if m:
            m.setup_signal_query()
            self.write('Signal query enabled')
        else:
            self.write('No modem found')


class ModemResetHandler(tornado.web.RequestHandler):
    def get(self):
        logger.warning('resetting modem')
        m = MM.modem()
        if m:
            m.reset()
            self.write('Modem reset successfully')
        else:
            self.write('No modem found')

class SystemRebootHandler(tornado.web.RequestHandler):
    def get(self):
        logger.warning('rebooting system')
        self.write('Initiated system reboot')
        os.system("reboot")


class CloudHandler(tornado.web.RequestHandler):
    def get(self):
        logger.warning('starting/stopping cloud logging service')
        enable = self.get_query_argument('enable', False)

        things = Things.instance
        res = things.enable(enable == 'True')
        self.write(res)


# TODO: Move to pagegnss.py
class GnssSaveStateHandler(tornado.web.RequestHandler):
    def get(self):
        gnss = Gnss.instance
        res = gnss.save_state()
        self.write(res)


class GnssClearStateHandler(tornado.web.RequestHandler):
    def get(self):
        gnss = Gnss.instance
        res = gnss.clear_state()
        self.write(res)


class GnssSaveConfigHandler(tornado.web.RequestHandler):
    def get(self):
        gnss = Gnss.instance
        res = gnss.save_config()
        self.write(res)


class GnssFactoryResetHandler(tornado.web.RequestHandler):
    def get(self):
        gnss = Gnss.instance
        res = gnss.reset_config()
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
        logger.debug(f'dynamic model {dyn_model}')

        auto_align = self.get_query_argument('auto_align', 0)
        logger.debug(f'auto_align {auto_align}')

        imu_cfg_angles = self.get_query_argument('imu_cfg_angles')
        logger.debug(f'imu_cfg_angles {imu_cfg_angles}')
        angles_as_int = imu_cfg_angles.split(',')
        angles = {
            'roll': int(float(angles_as_int[0]) * 100.0),
            'pitch': int(float(angles_as_int[1]) * 100.0),
            'yaw': int(float(angles_as_int[2]) * 100.0)
        }

        vrp_imu_values = self.get_query_argument('vrp_imu')
        logger.info(f'vrp_imu {vrp_imu_values}')
        vrp_imu_in_m = vrp_imu_values.split(',')
        vrp_imu = {
            'x': int(vrp_imu_in_m[0]),
            'y': int(vrp_imu_in_m[1]),
            'z': int(vrp_imu_in_m[2])
        }

        vrp_ant_values = self.get_query_argument('vrp_ant')
        logger.info(f'vrp_ant {vrp_ant_values}')
        vrp_ant_in_m = vrp_ant_values.split(',')
        vrp_ant = {
            'x': int(vrp_ant_in_m[0]),
            'y': int(vrp_ant_in_m[1]),
            'z': int(vrp_ant_in_m[2])
        }

        gnss = Gnss.instance

        res1 = gnss.set_dynamic_model(int(dyn_model))
        res2 = gnss.set_auto_align(auto_align == "On")
        res3 = gnss.set_imu_cfg_angles(angles)
        res4 = gnss.set_vrp_ant(vrp_ant)
        res5 = gnss.set_vrp_imu(vrp_imu)
        res = res1 + '<br>' + res2 + '<br>' + res3 + '<br>' + res4 + '<br>' + res5

        self.write(res)


class GsmCellLocateHandler(tornado.web.RequestHandler):
    def get(self):
        mcc = self.get_query_argument('mcc', 0)
        mnc = self.get_query_argument('mnc', 0)
        lac = self.get_query_argument('lac', 0)
        cid = self.get_query_argument('cid', 0)

        logger.debug(f'cellinfo: mcc {mcc}, mnc {mnc}, lac {lac}, cid {cid}')

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
                location = d['display_name']

                result += '</br>'
                result += f'{location}'

            result += '</br>'
            result += f'<a target="_blank" href="http://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=16">Link To OpenStreetMap</a>'

        else:
            result = 'Cell not found in opencellid database'

        self.write(result)


class NotImplementedHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('WARNING: Function not yet implemented')


def run_server(port=80):
    model = Model()
    model.setup()

    wwan = Wwan(model)
    wwan.setup()

    gnss = Gnss(model)
    gnss.setup()

    things = Things(model)
    things.setup()

    # Start cloud logging by default
    things.enable(True)

    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static")
    }

    app = tornado.web.Application([
        (r"/", MainHandler),
        (r"/gnss", GnssHandler),
        (r"/realtime", RealtimeHandler),

        (r"/do_location", LocationHandler),
        (r"/do_signal", SignalHandler),
        (r"/do_cell_locate", GsmCellLocateHandler),
        (r"/do_cloud", CloudHandler),
        (r"/do_modem_reset", ModemResetHandler),
        (r"/do_system_reboot", SystemRebootHandler),

        (r"/do_gnss_config", GnssConfigHandler),

        (r"/do_ser2net", NotImplementedHandler),
        (r"/do_gnss_state_save", GnssSaveStateHandler),
        (r"/do_gnss_state_clear", GnssClearStateHandler),
        (r"/do_gnss_settings_save", GnssSaveConfigHandler),
        (r"/do_gnss_factory_reset", GnssFactoryResetHandler),
        (r"/do_gnss_coldstart", GnssColdStartHandler),

        (r"/ws_realtime", RealtimeWebSocket),
    ], **settings)

    # logging.getLogger("tornado.access").setLevel(logging.DEBUG)
    # logging.getLogger("tornado.application").setLevel(logging.DEBUG)
    # logging.getLogger("tornado.general").setLevel(logging.DEBUG)

    try:
        app.listen(port)
    except OSError:
        logger.warning(f'server port {port} in use. Is another webserver running?')

    tornado.ioloop.IOLoop.current().start()


# Can be invoked with python3 -m vcuui.server
if __name__ == "__main__":
    run_server()
