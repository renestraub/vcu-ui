import re
import subprocess
from os import path

from vcuui.sysinfo_base import SysInfoBase


class SysInfoSensors(SysInfoBase):
    """
    System Info implementation using 'sensors' tool to retrieve values
    """
    BIN = '/usr/bin/sensors'

    @staticmethod
    def sensors_present():
        return path.exists(SysInfoSensors.BIN)

    def __init__(self):
        super().__init__()

        self.data = None
        self.temp_pmic = None
        self.temp_board = None
        self.volt_in = None
        self.volt_rtc = None

    def poll(self):
        cp = subprocess.run([SysInfoSensors.BIN], stdout=subprocess.PIPE)
        res = cp.stdout.decode().strip()
        self.sensor_res = res

        self.temp_pmic = self._extract('tjunc')
        self.temp_board = self._extract('temp1')
        self.volt_in = self._extract('input-voltage')
        self.volt_rtc = self._extract('rtc-voltage')

    def temperature(self):
        return self.temp_pmic

    def input_voltage(self):
        return self.volt_in

    def rtc_voltage(self):
        return self.volt_rtc

    def temperature_lm75(self):
        return self.temp_board

    def _extract(self, token):
        regex = rf"{token}:\s*([-+]?\d+.\d+)"
        match = re.search(regex, self.sensor_res, re.MULTILINE)
        if match and len(match.groups()) == 1:
            return float(match.group(1))
