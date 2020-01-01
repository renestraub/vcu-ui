import subprocess
import time


def secs_to_hhmm(secs):
    t = int((secs+30) / 60)
    h = int(t / 60)
    m = int(t % 60)
    return h, m


def ping(ip):
    cp = subprocess.run(['ping', '-c', '4', ip], stdout=subprocess.PIPE)
    res = cp.stdout.decode()

    return res


def nmcli_c():
    cp = subprocess.run(['nmcli', 'c'], stdout=subprocess.PIPE)
    res = cp.stdout.decode()

    return res


def start_ser2net():
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

    # ser2net
    res += '<br>(Re-)Starting ser2net: '
    subprocess.run(['killall', 'ser2net'], stdout=subprocess.PIPE)

    cp = subprocess.run(['ser2net', '-C', '2947:raw:0:/dev/gps0:115200'],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode == 0:
        res += 'Ok'
    else:
        res += 'Fail'

    return res
