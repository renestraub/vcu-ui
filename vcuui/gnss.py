import binascii
import subprocess
import time

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
