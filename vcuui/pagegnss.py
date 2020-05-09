"""
GNSS Page
"""
from bottle import template

from vcuui._version import __version__ as version
from vcuui.data_model import Model
from vcuui.gnss_model import Gnss


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


def build_gnss():
    try:
        tes = list()
        data = dict()

        # General System Information
        m = Model.instance
        md = m.get_all()

        serial = md['sys-version']['serial']

        gnss = Gnss.instance
        gnss.invalidate()

        # GNSS Version

        print("1")
        ver = gnss.version()
        print(ver)
        tes.append(TE('Version', ''))
        tes.append(TE('HW', ver['hwVersion']))
        tes.append(TE('SW', ver['swVersion']))
        tes.append(TE('FW', ver['fwVersion']))
        tes.append(TE('Protocol', ver['protocol']))
        tes.append(TE('', ''))

        # GNSS Status (live)
        if 'gnss-pos' in md:
            print("2")
            tes.append(TE('Status', ''))

            pos = md['gnss-pos']
            tes.append(TE('Fix', pos['fix']))
            text = f'Longitude: {pos["lon"]:.9f}, Latitude: {pos["lat"]:.9f}'
            tes.append(TE('Position', text))
            text = nice([('speed', '', 'km/h')], pos)
            tes.append(TE('Speed', f'{pos["speed"]:.0f} m/s, {pos["speed"]*3.60:.0f} km/h'))
            # tes.append(TE('', ''))

        # Config
        print("3")
        data['dyn_model'] = str(gnss.dynamic_model())
        print("4")
        data['nmea_protocol'] = gnss.nmea_protocol()

        print("5")
        uart_cfg = gnss.uart_settings()
        data['uart_settings'] = f'{uart_cfg["bitrate"]} bps, {uart_cfg["mode"]}'

        print("6")
        align = gnss.auto_align()
        data['imu_auto_align'] = 'On' if align else 'Off'

        print("7")
        align_state = gnss.auto_align_state()
        data['imu_auto_align_state'] = align_state

        print("8")
        cfg_angles = gnss.imu_cfg_angles()
        data['imu_cfg_roll'] = str(round(cfg_angles['roll']))
        data['imu_cfg_pitch'] = str(round(cfg_angles['pitch']))
        data['imu_cfg_yaw'] = str(round(cfg_angles['yaw']))

        print("9")
        roll, pitch, yaw = gnss.auto_align_angles()
        angles_str = f'roll: {roll}°, pitch: {pitch}°, yaw: {yaw}°'
        data['imu_angles'] = angles_str

        print("10")
        esf_status = gnss.esf_status()
        text = nice([('fusion', 'Fusion', ''),
                    ('ins', 'INS', ''),
                    ('imu', 'IMU', ''),
                    ('imu-align', 'IMU Alignment', '')],
                    esf_status)
        data['esf_status'] = text

        print(data)

        output = template('gnss',
                          title=f'VCU Pro ({serial})',
                          table=tes,
                          data=data,
                          message='',
                          version=version)

    except KeyError as e:
        print(e)
        output = template('gnss',
                          title='VCU Pro',
                          message=f'Data lookup error: {e} not found',
                          table=None,
                          data=None,
                          version='n/a')

    return output
