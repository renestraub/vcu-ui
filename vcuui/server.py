"""
Minimal Web UI for VCU automotive gateway

Uses bottle webserver in single threading mode
"""

import json
import os

import bottle
import requests
from bottle import Bottle, post, request, route, run, static_file

from vcuui._version import __version__ as version
from vcuui.gnss import save_state, start_ser2net
from vcuui.mm import MM
from vcuui.data_model import Model
from vcuui.pageinfo import render_page
from vcuui.tools import ping
from vcuui.things import Things


# Init section
print(f'Welcome to VCU-UI v{version}')

path = os.path.abspath(__file__)
module_path = os.path.dirname(path)
bottle.TEMPLATE_PATH.insert(0, module_path)
print(f'Running server from {module_path}')

app = Bottle()
bottle.debug(True)


# Static CSS Files
# Static text Files
@app.route(r'<filename:re:.*\.txt>')
@app.route(r'<filename:re:.*\.css>')
def send_css(filename):
    return static_file(filename, root=module_path)


@app.route('/do_ping')
def do_ping():
    console = ping('1.1.1.1')
    return console


@app.route('/do_location')
def do_location():
    m = MM.modem()
    m.setup_location_query()
    return '3GPP Location query enabled'


@app.route('/do_signal')
def do_signal():
    m = MM.modem()
    m.setup_signal_query()
    return 'Signal quality measurements enabled'


@app.route('/do_modem_reset')
def do_modem_reset():
    m = MM.modem()
    m.reset()
    return 'Modem reset successfully'


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


@app.route('/do_cloud', method='GET')
def do_cloud():
    enable = request.query['enable']
    print(f'cloud logger new state {enable}')

    things = Things.instance
    res = things.start2(enable == 'True')
    return res


# Mainpage
@app.route('/')
def info():
    return render_page()


def run_server(port=80):
    model = Model()
    model.setup()

    # TODO: ThingsBoard updater
    things = Things(model)
    things.setup()

    # Start cloud logging by default
    things.start2(True)

    app.run(host='0.0.0.0', port=port)
    # run(host='0.0.0.0', port=port, debug=True, reloader=True)


# Can be invoked with python3 -m vcuui.server
if __name__ == "__main__":
    run_server()
