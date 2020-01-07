# import serial
import subprocess
import time

import binascii

try:
    # Allow this to fail, so we can execute unit tests with pyserial
    import serial
except ImportError:
    pass


def start_ser2net():
    """
    Starts ser2net tool for connection with u-Center
    """
    res = ''

    res += _stop_services()
    res += _stop_ser2net()

    res += _start_ser2net()

    return res


def save_state():
    """
    Saves receiver state for next power up

    This saves DR states and others, so that navigation can immediately
    continue once power is back ription]
    """
    res = ''

    ser = serial.Serial('/dev/gps0', 115200, timeout=0.1)

    # Stop services that would interfere with operation
    res += _stop_services()
    res += _stop_ser2net()

    # Save state with receiver stopped
    res += _stop_receiver(ser)
    res += _save_state(ser)
    res += _start_receiver(ser)

    return res


def _start_receiver(ser):
    print('start receiver')
    res = ''
    res += '<br>Restarting GNSS module: '

    _send_msg(ser, bytearray.fromhex('06 04 04 00 00 00 09 00'))
    if _expect_text(ser, 'Starting'):
        res += 'Ok'
    else:
        res += 'Failed'

    return res


def _stop_receiver(ser):
    print('stop receiver')
    res = ''
    res += '<br>Stopping GNSS module: '

    _send_msg(ser, bytearray.fromhex('06 04 04 00 00 00 08 00'))
    if _expect_text(ser, 'Stopping'):
        res += 'Ok'
    else:
        res += 'Failed'

    return res


def _save_state(ser):
    res = ''
    res += '<br>Saving state to flash memory: '

    _send_msg(ser, bytearray.fromhex('09 14 04 00 00 00 00 00'))
    if _expect_hex(ser, bytearray.fromhex('62 09 14 08 00 02 00 00 00 01 00 '
                                          '00')):
        res += 'Ok'
    else:
        res += 'Failed'

    return res


def _send_msg(ser, msg):
    ubx_msg = _create_ubx_message(msg)
    ser.reset_input_buffer()
    ser.write(ubx_msg)


def _expect_text(ser, text):
    t_end = time.time() + 2.0
    while time.time() < t_end:
        line = ser.readline()
        print(binascii.hexlify(line))
        if line == b'':
            return False

        try:
            line = line.decode('ascii')
            # print(line)
            if text in line:
                return True

        except UnicodeDecodeError:
            pass


def _expect_hex(ser, hex):
    data = bytearray()
    t_end = time.time() + 1.0
    while time.time() < t_end:
        line = ser.read(8)
        # print(binascii.hexlify(line))
        data += line
        pos = data.find(hex)
        # print(pos)
        if pos != -1:
            return True


def _create_ubx_message(data):
    cka, ckb = _calc_checksum(data)
    msg = bytearray(b'\xb5\x62') + data
    msg.append(cka)
    msg.append(ckb)
    return msg


def _calc_checksum(data):
    cka = 0
    ckb = 0

    for byte in data:
        cka += byte
        cka &= 0xFF
        ckb += cka
        ckb &= 0xFF

    return cka, ckb


def _stop_services():
    res = ''

    # gpsd
    cp = subprocess.run(['systemctl', 'status', 'gpsd'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode == 0:
        res = '<br>Trying to stop gpsd (and gpsd.service): '
        cp1 = subprocess.run(['systemctl', 'stop', 'gpsd'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        cp2 = subprocess.run(['systemctl', 'stop', 'gpsd.service'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if cp1.returncode == 0 and cp2.returncode == 0:
            res += 'Ok'
        else:
            res += 'Fail'

    # gpslog (privat development tool)
    cp = subprocess.run(['systemctl', 'status', 'gpslog'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode == 0:
        res += '<br>Trying to stop gpslog: '
        cp = subprocess.run(['systemctl', 'stop', 'gpslog'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if cp.returncode == 0:
            res += 'Ok'
        else:
            res += 'Fail'

    time.sleep(1.0)

    return res


def _start_ser2net():
    res = ''
    res += '<br>Starting ser2net: '

    cp = subprocess.run(['ser2net', '-C', '2947:raw:0:/dev/gps0:115200'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode == 0:
        res += 'Ok'
    else:
        res += 'Fail'

    return res


def _stop_ser2net():
    res = ''
    res += '<br>Stopping ser2net'

    subprocess.run(['killall', 'ser2net'], stdout=subprocess.PIPE)

    return res
