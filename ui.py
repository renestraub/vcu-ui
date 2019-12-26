#!/usr/bin/python3

"""
Minimal Web UI for VCU

Uses bootle webserver in single thread mode

pip3 install bottle
"""

from bottle import route, run, post, template, static_file, request
from mm import MM
from sysinfo import SysInfo


class TE():
    """
    Table Element to be displayed in info.tpl
    """
    def __init__(self, header, text):
        self.header = header
        self.text = text


def render_page(message = None):
    tes = list()

    si = SysInfo()
    tes.append(TE('System', ''))

    dt = si.date()
    tes.append(TE('Date', dt))

    ver = si.version()
    tes.append(TE('Version', ver))

    total, free = si.meminfo()
    tes.append(TE('Memory', f'Total {total} kB, Free {free} kB'))

    a, b, c = si.load()
    tes.append(TE('Load', f'{a}, {b}, {c}'))


    tes.append(TE('Network', ''))

    rx, tx = si.ifinfo('wwan0')
    rx = int(rx) / 1000000
    tx = int(tx) / 1000000
    tes.append(TE('wwan0', f'Rx: {rx:.1f} MB, Tx {tx:.1f} MB'))


    tes.append(TE('Mobile', ''))

    m = MM.modem()
    tes.append(TE('Modem', str(m.id)))

    state = m.state()
    tes.append(TE('State', state))

    sq = m.signal()
    tes.append(TE('Signal', f'{sq} %'))

    a, b = m.signal_lte()
    tes.append(TE('Signal LTE', f'{a} dBm {b} dBm'))


    b = m.bearer()
    tes.append(TE('Bearer', str(b.id)))
    ut = b.uptime()
    tes.append(TE('Uptime', ut))
    ip = b.ip()
    tes.append(TE('IP', ip))

    output = template('info', data=tes, message=message)
    return output


# Static CSS Files
# @route('/static/css/<filename:re:.*\.css>')
@route('<filename:re:.*\.css>')
def send_css(filename):
    return static_file(filename, root='')

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

    else:
        msg = None

    return render_page(msg)

# Mainpage
@route('/')
@route('/info')
def info():
    return render_page()


run(host='0.0.0.0', port=80, debug=True, reloader=True)
