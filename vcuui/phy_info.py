import logging
import os

logger = logging.getLogger('vcu-ui')


class PhyInfo:
    def __init__(self, interface):
        self.__if = interface

        try:
            # Check phydev entry which contains phy_id at end
            # ../../../../../../4a100000.ethernet/4a101000.mdio/mdio_bus/4a101000.mdio/4a101000.mdio:03
            if_node = '/sys/class/net/{}/phydev'.format(self.__if)
            link_to_phy_dev = os.readlink(if_node)
            phy_id = link_to_phy_dev.split(':')[1]

            self.__sys_node = '/sys/bus/mdio_bus/devices/4a101000.mdio:{}/configuration/'.format(phy_id)

        except FileNotFoundError:
            print("error")
            self.__sys_node = None

    def state(self):
        if self.__sys_node:
            link = 'down'

            with open(self.__sys_node + 'link_status') as f:
                link = f.readline().strip()

            return link

    def quality(self):
        if self.__sys_node:
            qual = 0

            with open(self.__sys_node + 'snr_class') as f:
                quality = f.readline().strip()

                if 'Class A' in quality:
                    qual = 0
                elif 'Class B' in quality:
                    qual = 16
                elif 'Class C' in quality:
                    qual = 33
                elif 'Class D' in quality:
                    qual = 50
                elif 'Class E' in quality:
                    qual = 66
                elif 'Class F' in quality:
                    qual = 83
                elif 'Class G' in quality:
                    qual = 100

            return qual
