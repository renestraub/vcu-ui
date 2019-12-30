"""
Minimal Web UI for VCU automotive gateway

Uses bootle webserver in single thread mode
"""

import os

import bottle
import requests
from bottle import Bottle, post, request, route, run, static_file

from vcuui._version import __version__ as version
from vcuui.mm import MM
from vcuui.pageinfo import render_page
from vcuui.tools import nmcli_c, ping


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
    # m.reset()
    return 'Modem reset successfully'


@app.route('/do_cell_locate', method='GET')
def do_cell_locate(mcc='0'):
    print('cell locate')
    mcc = request.query['mcc']
    mnc = request.query['mnc']
    lac = request.query['lac']
    cid = request.query['cid']
    cid = 17538051      # 17538057 not known
    print(f'cellinfo: mcc {mcc}, mnc {mnc}, lac {lac}, cid {cid}')

    # https://opencellid.org/ajax/searchCell.php?mcc=228&mnc=1&lac=3434&cell_id=17538051
    args = {'mcc': mcc, 'mnc': mnc, 'lac': lac, 'cell_id': cid}
    r = requests.get("https://opencellid.org/ajax/searchCell.php", params=args)
    print(r.url)
    print(f'result: {r.text}')
    print(type(r.text))

    # return r.text
    return r'<a target="_blank" href="http://www.openstreetmap.org/?mlat=47.321667&mlon=7.981032&zoom=16">Link To OpenStreetMap</a>'


# Mainpage
@app.route('/')
def info():
    return render_page()


def run_server(port=80):
    # run(host='0.0.0.0', port=port, debug=True, reloader=True)
    app.run(host='0.0.0.0', port=port)


# Can be invoked with python3 -m vcuui.ui
if __name__ == "__main__":
    run_server()
