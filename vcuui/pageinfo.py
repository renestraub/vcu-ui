"""
Info Page
"""
from bottle import template

from vcuui._version import __version__ as version
from vcuui.tools import secs_to_hhmm
from vcuui.mm import MM
from vcuui.sysinfo import SysInfo


class TE(object):
    """
    Table Element to be displayed in info.tpl
    """
    def __init__(self, header, text):
        self.header = header
        self.text = text


def nice(items, data, linebreak=False):
    res = ''
    for i in items:
        key, header, unit = i
        val = data[key]
        if res != '':
            if linebreak:
                res += '</br>'
            else:
                res += ', '

        res += f'{header}: {val}'
        if unit != '':
            res += f' {unit}'

    return res


def render_page(message=None, console=None):
    tes = list()
    data = dict()

    # General System Information
    si = SysInfo()
    tes.append(TE('System', ''))

    dt = si.date()
    tes.append(TE('Date', dt))

    ver = si.version()
    tes.append(TE('Version', ver))

    total, free = si.meminfo()
    tes.append(TE('Memory', f'Total: {total} kB<br>Free: {free} kB'))

    a, b, c = si.load()
    tes.append(TE('Load', f'{a}, {b}, {c}'))

    temp = si.temperature()
    tes.append(TE('Temperature', f'{temp:.0f} °C'))

    v_in = si.input_voltage()
    v_rtc = si.rtc_voltage()
    tes.append(TE('Voltages', f'Input: {v_in:.1f} V, RTC: {v_rtc:.2f} V'))

    # Network Information
    tes.append(TE('', ''))
    tes.append(TE('Network', ''))

    rx, tx = si.ifinfo('wwan0')
    if rx and tx:
        rx = int(rx) / 1000000
        tx = int(tx) / 1000000
        tes.append(TE('wwan0', f'Rx: {rx:.1f} MB<br>Tx: {tx:.1f} MB'))

    tes.append(TE('', ''))
    tes.append(TE('Mobile', ''))

    # Modem Information
    m = MM.modem()
    if m:
        tes.append(TE('Modem Id', str(m.id)))

        state = m.state()
        access_tech = m.access_tech()
        tes.append(TE('State', f'{state}, {access_tech}'))

        loc_info = m.location()
        if loc_info['mcc']:
            text = nice([('mcc', 'MCC', ''),
                         ('mnc', 'MNC', ''),
                         ('lac', 'LAC', ''),
                         ('cid', 'CID', '')],
                        loc_info)
            tes.append(TE('Cell', text))
            data.update(loc_info)

        sq = m.signal()
        tes.append(TE('Signal', f'{sq} %'))

        if access_tech == 'lte':
            sig = m.signal_lte()
            text = nice([('rsrp', 'RSRP', 'dBm'),
                         ('rsrq', 'RSRQ', 'dBm')],
                        sig, True)
            tes.append(TE('Signal LTE', text))
        elif access_tech == 'umts':
            sig = m.signal_umts()
            text = nice([('rscp', 'RSRP', 'dBm'),
                         ('ecio', 'ECIO', 'dBm')],
                        sig, True)
            tes.append(TE('Signal UMTS', text))

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

    output = template('main',
                      table=tes,
                      data=data,
                      message=message,
                      console=console,
                      version=version)

    return output
