"""
Minimal Web UI for VCU automotive gateway

Uses bootle webserver in single thread mode
"""

import os
import bottle
from bottle import run, post, request, route
from bottle import static_file, template

from vcuui._version import __version__ as version
from .mm import MM
from .sysinfo import SysInfo


# Init section
print(f'Welcome to VCU-UI v{version}')

path = os.path.abspath(__file__)
module_path = os.path.dirname(path)
print(f'Running server from {module_path}')
bottle.TEMPLATE_PATH.insert(0, module_path)


class TE():
    """
    Table Element to be displayed in info.tpl
    """
    def __init__(self, header, text):
        self.header = header
        self.text = text


def secs_to_hhmm(secs):
    t = int(secs / 60)
    h = int(t / 60)
    m = int(t % 60)
    return h, m


def render_page(message = None):
    tes = list()

    si = SysInfo()
    tes.append(TE('System', ''))

    dt = si.date()
    tes.append(TE('Date', dt))

    ver = si.version()
    tes.append(TE('Version', ver))

    total, free = si.meminfo()
    tes.append(TE('Memory', f'Total {total} kB<br>Free {free} kB'))

    a, b, c = si.load()
    tes.append(TE('Load', f'{a}, {b}, {c}'))

    temp = si.temperature()
    tes.append(TE('Temperature', f'{temp:.0f} °C'))

    tes.append(TE('', ''))
    tes.append(TE('Network', ''))

    rx, tx = si.ifinfo('wwan0')
    if rx and tx:
        rx = int(rx) / 1000000
        tx = int(tx) / 1000000
        tes.append(TE('wwan0', f'Rx {rx:.1f} MB<br>Tx {tx:.1f} MB'))


    tes.append(TE('', ''))
    tes.append(TE('Mobile', ''))

    m = MM.modem()
    if m:
        tes.append(TE('Modem Id', str(m.id)))

        state = m.state()
        tes.append(TE('State', state))

        sq = m.signal()
        tes.append(TE('Signal', f'{sq} %'))

        a, b = m.signal_lte()
        if a and b:
            tes.append(TE('Signal LTE', f'{a} dBm<br>{b} dBm'))

        tes.append(TE('', ''))
        b = m.bearer()
        if b:        
            tes.append(TE('Bearer Id', str(b.id)))
            ut = b.uptime()
            if ut:
                uth, utm = secs_to_hhmm(ut)
                tes.append(TE('Uptime', f'{uth}:{utm:02} h'))
                ip = b.ip()
                tes.append(TE('IP', ip))
    else:
        tes.append(TE('Modem Id', 'No Modem'))

    output = template('info', data=tes, message=message)
    return output


# Static CSS Files
# @route('/static/css/<filename:re:.*\.css>')
@route(r'<filename:re:.*\.css>')
def send_css(filename):
    return static_file(filename, root=module_path)


# Action handler
@post('/action')
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

    return render_page(msg)


# Mainpage
@route('/')
@route('/info')
def info():
    return render_page()


def run_server(port=80):
    # run(host='0.0.0.0', port=port, debug=True, reloader=True)
    run(host='0.0.0.0', port=port, debug=True)


# Can be invoked with python3 -m vcuui.ui
if __name__ == "__main__":
    run_server()
