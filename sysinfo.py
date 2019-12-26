import subprocess


class SysInfo():
    def __init__(self):
        pass

    def version(self):
        with open('/etc/version') as f:
            res = f.readline()

        return res

    def meminfo(self):
        with open('/proc/meminfo') as f:
            res = f.readlines()
            for line in res:
                if 'MemTotal' in line:
                    total = line.split()[1].strip()
                elif 'MemFree' in line:
                    free = line.split()[1].strip()

        return total, free

    def load(self):
        with open('/proc/loadavg') as f:
            res = f.readline()
            info = res.split()
            # print(info)
            return info[0:3]

    def date(self):
        cp = subprocess.run(['date'], stdout=subprocess.PIPE)
        res = cp.stdout.decode()
        return res

    def ifinfo(self, name):
        path = f'/sys/class/net/{name}/statistics/rx_bytes'
        with open(path) as f:
            rxbytes = f.readline().strip()

        path = f'/sys/class/net/{name}/statistics/tx_bytes'
        with open(path) as f:
            txbytes = f.readline().strip()

        return rxbytes, txbytes
