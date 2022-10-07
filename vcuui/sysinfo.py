import subprocess
from os import path


class SysInfo():
    def __init__(self):
        # Locate PMIC hwmon

        # From kernel 5.10.x on, PMIC path changes to the following
        # /sys/bus/platform/drivers/da9063-hwmon/da9063-hwmon/hwmon/hwmon1/
        path_5_10 = '/sys/bus/platform/drivers/da9063-hwmon/da9063-hwmon/hwmon/hwmon1/'
        if path.exists(path_5_10):
            print("using new path")
            self.da9063_path = path_5_10
        else:
            self.da9063_path = '/sys/bus/platform/drivers/da9063-hwmon/da9063-hwmon'

        # Optional LM75 sensor (NG800 devices)
        self.lm75_path = '/sys/bus/i2c/drivers/lm75/1-0048/hwmon/hwmon1'

    def serial(self):
        with open('/sys/class/net/eth0/address') as f:
            res = f.readline().strip().upper()

        return res

    def version(self):
        with open('/etc/version') as f:
            res = f.readline().strip()
            res = res.replace(';', ', ')

        return res

    def bootloader_version(self):
        with open('/proc/device-tree/nm,bootloader,version') as f:
            res = f.readline().strip()
            res = res.rstrip('\0x00')

        return res

    def hw_version(self):
        with open('/proc/device-tree/nm,carrierboard,version') as f:
            res = f.readline().strip()
            res = res.rstrip('\0x00')

        return res

    def start_reason(self):
        try:
            with open('/sys/kernel/broker/start-reason') as f:
                res = f.readline().strip()

            return res
        except FileNotFoundError:
            return "unknown"

    def meminfo(self):
        with open('/proc/meminfo') as f:
            res = f.readlines()
            for line in res:
                if 'MemTotal' in line:
                    total = line.split()[1].strip()
                elif 'MemFree' in line:
                    free = line.split()[1].strip()

        return total, free

    def part_size(self, partition):
        cp = subprocess.run(['df', '-h', partition], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()
        for line in res.splitlines():
            if partition in line:
                res = line

        return res

    def emmc_wear(self):
        """
        Check for following output in mmc command
        eMMC Life Time Estimation A [EXT_CSD_DEVICE_LIFE_TIME_EST_TYP_A]: 0x01
        """
        cp = subprocess.run(['mmc', 'extcsd', 'read', '/dev/mmcblk1'], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()

        res_a = 0
        res_b = 0
        for line in res.splitlines():
            if 'Life Time Estimation' in line:
                if 'TYP_A' in line:
                    res_a = int(line[-2:], 16) * 10.0
                if 'TYP_B' in line:
                    res_b = int(line[-2:], 16) * 10.0

        return res_a, res_b

    def load(self):
        with open('/proc/loadavg') as f:
            res = f.readline()
            info = res.split()
            return info[0:3]

    def date(self):
        cp = subprocess.run(['date'], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()
        return res

    def uptime(self):
        cp = subprocess.run(['uptime'], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()
        start = res.find("up")
        end = res.find(",  load")
        return res[start:end]

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
        with open(f'{self.da9063_path}/temp1_input') as f:
            temp_in_milli_c = f.readline().strip()
            return round(float(temp_in_milli_c) / 1000.0, 1)

    def input_voltage(self):
        with open(f'{self.da9063_path}/in1_input') as f:
            adc_millivolts = f.readline().strip()
            return round(float(adc_millivolts) / 1000.0 * 15.0, 1)

    def rtc_voltage(self):
        with open(f'{self.da9063_path}/in4_input') as f:
            adc_millivolts = f.readline().strip()
            return round(float(adc_millivolts) / 1000.0, 3)

    def temperature_lm75(self):
        # TODO: Test
        try:
            with open(f'{self.lm75_path}/temp_input') as f:
                temp_in_milli_c = f.readline().strip()
                return round(float(temp_in_milli_c) / 1000.0, 1)
        except FileNotFoundError:
            pass
