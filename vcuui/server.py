"""
Minimal Web UI for VCU automotive gateway

Uses bootle webserver in single thread mode
"""

import os

import bottle
from bottle import Bottle, post, request, route, run, static_file

from vcuui._version import __version__ as version
from vcuui.pageinfo import render_page
from vcuui.mm import MM


# Init section
print(f'Welcome to VCU-UI v{version}')

path = os.path.abspath(__file__)
module_path = os.path.dirname(path)
print(f'Running server from {module_path}')
bottle.TEMPLATE_PATH.insert(0, module_path)

app = Bottle()
bottle.debug(True)


# Static CSS Files
# @route('/static/css/<filename:re:.*\.css>')
@app.route(r'<filename:re:.*\.css>')
def send_css(filename):
    return static_file(filename, root=module_path)


# Action handler
@app.post('/action')
def action():
    method = request.forms.get('method')
    print(f'method {method} selected')

    if method == 'signal-query':
        print("Enabling signal query on modem")
        m = MM.modem()
        m.setup_signal_query()

        msg = 'Signal measurement enabled'

    elif method == 'reset-modem':
        m = MM.modem()
        m.reset()

        msg = 'Modem resetted'

    else:
        msg = None

    return info.render_page(msg)


# Mainpage
@app.route('/')
@app.route('/info')
def info():
    return render_page()


def run_server(port=80):
    # run(host='0.0.0.0', port=port, debug=True, reloader=True)
    app.run(host='0.0.0.0', port=port)


# Can be invoked with python3 -m vcuui.ui
if __name__ == "__main__":
    run_server()
