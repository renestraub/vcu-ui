import logging
import subprocess

logger = logging.getLogger('vcu-ui')


class VnStat:
    BIN = 'vnstat'

    @classmethod
    def probe(cls):
        # Check if tool is installed
        try:
            vnstat_call = [VnStat.BIN, '--version']
            cp = subprocess.run(vnstat_call, capture_output=True)
            if cp.returncode == 0:
                VnStat.version = cp.stdout
                return True

        except FileNotFoundError:
            logger.info(f'{VnStat.BIN} not found')

    def __init__(self, interface):
        self.__if = interface

    def get(self):
        logger.debug(f'getting traffic for {self.__if}')

        try:
            vnstat_call = [VnStat.BIN, '-d', '--oneline', 'b']
            cp = subprocess.run(vnstat_call, capture_output=True)
            if cp.returncode == 0:
                result = cp.stdout.decode().strip().split(';')

                rx_day = result[3]
                tx_day = result[4]
                rx_month = result[8]
                tx_month = result[9]
                rx_year = result[12]
                tx_year = result[13]

                info = {
                    'day_rx': int(rx_day),
                    'day_tx': int(tx_day),
                    'month_rx': int(rx_month),
                    'month_tx': int(tx_month),
                    'year_rx': int(rx_year),
                    'year_tx': int(tx_year)
                }
                return info

        except FileNotFoundError:
            logger.info(f'{VnStat.BIN} not found')
