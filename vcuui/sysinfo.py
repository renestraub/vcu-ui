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
        try:
            path = f'/sys/class/net/{name}/statistics/rx_bytes'
            with open(path) as f:
                rxbytes = f.readline().strip()

            path = f'/sys/class/net/{name}/statistics/tx_bytes'
            with open(path) as f:
                txbytes = f.readline().strip()

        except FileNotFoundError:
            rxbytes, txbytes = None, None

        return rxbytes, txbytes

    def temperature(self):
        with open('/sys/class/hwmon/hwmon0/device/temp1_input') as f:
            temp_in_milli_c = f.readline().strip()
            return float(temp_in_milli_c) / 1000.0

    def input_voltage(self):
        with open('/sys/class/hwmon/hwmon0/device/in1_input') as f:
            adc_millivolts = f.readline().strip()
            return float(adc_millivolts) / 1000.0 * 15.0

    def rtc_voltage(self):
        with open('/sys/class/hwmon/hwmon0/device/in4_input') as f:
            adc_millivolts = f.readline().strip()
            return float(adc_millivolts) / 1000.0
