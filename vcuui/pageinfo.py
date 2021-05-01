"""
Main Page (Single Page)
"""
import logging

import tornado.web

from vcuui._version import __version__ as version
from vcuui.data_model import Model
from vcuui.tools import secs_to_hhmm

logger = logging.getLogger('vcu-ui')


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


class Data():
    def __init__(self, data):
        super().__init__()
        self._data = data

    def get(self, default, *keys):
        dct = self._data
        for key in keys:
            try:
                dct = dct[key]
            except KeyError as e:
                logger.debug(f'cannot get {e}')
                return default
        return dct


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render_page()

    def render_page(self, message=None, console=None):
        logger.info('rendering page')

        try:
            tes = list()
            data = dict()

            # General System Information
            m = Model.instance
            md = m.get_all()
            d = Data(md)

            cloud_log_state = md['cloud']
            serial = d.get('N/A', 'sys-version', 'serial')

            tes.append(TE('<b>System</b>', ''))
            text = nice([('sys', 'System', ''),
                        ('bl', 'Bootloader', ''),
                        ('hw', 'Hardware', '')],
                        md['sys-version'], True)
            tes.append(TE('Version', text))

            dt = d.get('N/A', 'sys-datetime', 'date')
            tes.append(TE('Date', dt))

            ut = d.get('N/A', 'sys-datetime', 'uptime')
            tes.append(TE('Uptime', ut))

            total, free = d.get((0, 0), 'sys-misc', 'mem')
            tes.append(TE('Memory', f'Total: {total} kB<br>Free: {free} kB'))

            wear_slc, wear_mlc = d.get((0, 0), 'sys-disc', 'wear')
            sysroot_info = d.get('N/A', 'sys-disc', 'part_sysroot')
            data_info = d.get('N/A', 'sys-disc', 'part_data')
            tes.append(TE('Disc', f'eMMC Wear Level: SLC: {wear_slc} %, MLC: {wear_mlc} %<br>'
                                  f'Root: {sysroot_info}<br>'
                                  f'Data: {data_info}'))

            a, b, c = d.get((0, 0, 0), 'sys-misc', 'load')
            tes.append(TE('Load', f'{a}, {b}, {c}'))

            temp = d.get(0, 'sys-misc', 'temp')
            temp_str = f'PMIC: {temp:.0f} °C'
            temp = d.get(None, 'sys-misc', 'temp_lm75')
            if temp:
                temp_str += f', Board: {temp:.0f} °C'
            tes.append(TE('Temperature', temp_str))

            v_in = md['sys-misc']['v_in']
            v_rtc = md['sys-misc']['v_rtc']
            tes.append(TE('Voltages', f'Input: {v_in:.1f} V, RTC: {v_rtc:.2f} V'))

            # Network Information
            tes.append(TE('', ''))
            tes.append(TE('<b>Network</b>', ''))

            rx, tx = d.get((-1, -1), 'net-wwan0', 'bytes')
            if rx != -1:
                rx = int(rx) / 1000000
                tx = int(tx) / 1000000
                tes.append(TE('wwan0', f'Rx: {rx:.1f} MB<br>Tx: {tx:.1f} MB'))

            rx, tx = d.get((-1, -1), 'net-wlan0', 'bytes')
            if rx != -1:
                rx = int(rx) / 1000000
                tx = int(tx) / 1000000
                tes.append(TE('wlan0', f'Rx: {rx:.1f} MB<br>Tx: {tx:.1f} MB'))

            # Modem Information
            mi = md['modem']
            if 'modem-id' in mi:
                tes.append(TE('', ''))
                tes.append(TE('<b>Mobile</b>', ''))

                tes.append(TE('Modem Id', mi['modem-id']))

                state = mi['state']
                access_tech = mi['access-tech']
                tes.append(TE('State', f'{state}, {access_tech}'))

                if 'location' in mi:
                    loc_info = mi['location']
                    if loc_info['mcc']:
                        text = nice([('mcc', 'MCC', ''),
                                    ('mnc', 'MNC', ''),
                                    ('lac', 'LAC', ''),
                                    ('cid', 'CID', '')],
                                    loc_info)
                        tes.append(TE('Cell', text))
                        data.update(loc_info)

                sq = mi['signal-quality']
                tes.append(TE('Signal', f'{sq} %'))

                if access_tech == 'lte':
                    sig = mi['signal-lte']
                    text = nice([('rsrp', 'RSRP', 'dBm'),
                                ('rsrq', 'RSRQ', 'dB')],
                                sig, True)
                    tes.append(TE('Signal LTE', text))
                elif access_tech == 'umts':
                    sig = mi['signal-umts']
                    text = nice([('rscp', 'RSRP', 'dBm'),
                                ('ecio', 'ECIO', 'dB')],
                                sig, True)
                    tes.append(TE('Signal UMTS', text))

                if 'bearer-id' in mi:
                    tes.append(TE('', ''))
                    tes.append(TE('Bearer Id', mi['bearer-id']))

                    if 'bearer-uptime' in mi:
                        ut = mi['bearer-uptime']
                        if ut:
                            uth, utm = secs_to_hhmm(ut)
                            tes.append(TE('Uptime', f'{uth}:{utm:02} h'))
                            ip = mi['bearer-ip']
                            tes.append(TE('IP', ip))

                    if 'link' in md:
                        if 'delay' in md['link']:
                            delay_in_ms = md['link']['delay'] * 1000.0
                            tes.append(TE('Ping', f'{delay_in_ms:.0f} ms'))

                if 'sim-id' in mi:
                    tes.append(TE('', ''))
                    tes.append(TE('SIM Id', mi['sim-id']))
                    tes.append(TE('IMSI', mi['sim-imsi']))
                    tes.append(TE('ICCID', mi['sim-iccid']))

            else:
                tes.append(TE('', ''))
                tes.append(TE('Modem Id', 'No Modem'))

            # GNSS
            if 'gnss-pos' in md:
                tes.append(TE('', ''))
                tes.append(TE('<b>GNSS</b>', ''))

                pos = md['gnss-pos']
                tes.append(TE('Fix', pos['fix']))
                text = f'Longitude: {pos["lon"]:.9f}, Latitude: {pos["lat"]:.9f}'
                tes.append(TE('Position', text))
                text = nice([('speed', '', 'km/h')], pos)
                tes.append(TE('Speed', f'{pos["speed"]:.0f} m/s, {pos["speed"]*3.60:.0f} km/h'))

            # OBD-II
            if 'obd2' in md:
                tes.append(TE('', ''))
                tes.append(TE('<b>OBD-II</b>', ''))
                speed = md['obd2']['speed']
                tes.append(TE('Speed', f'{speed/3.60:.0f} m/s, {speed:.0f} km/h'))

            # OBD-II
            if 'phy-broadr0' in md:
                state = md['phy-broadr0']
                tes.append(TE('', ''))
                tes.append(TE('<b>100BASE-T1</b>', ''))
                tes.append(TE('BroadR0', f'{state["state"]}, {state["quality"]} %'))

            self.render('main.html',
                        title=f'{serial}',
                        table=tes,
                        data=data,
                        message=message,
                        console=console,
                        version=version,
                        cloud_log=cloud_log_state)

        except KeyError as e:
            logger.warning(f'lookup error {e}')
            self.render('main.html',
                        title='NG800/VCU Pro',
                        message=f'Data lookup error: {e} not found',
                        table=None,
                        data=None,
                        console=None,
                        version='n/a',
                        cloud_log=False)
