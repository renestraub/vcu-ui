import time
import threading
#from gps import *
#from ping3 import ping, verbose_ping

# from vcuui.sysinfo import SysInfo
#from vcuui.mm import MM

from ubxlib.server import GnssUBlox
from ubxlib.ubx_ack import UbxAckAck
# from ubxlib.ubx_cfg_tp5 import UbxCfgTp5Poll, UbxCfgTp5
# from ubxlib.ubx_upd_sos import UbxUpdSosPoll, UbxUpdSos, UbxUpdSosAction
from ubxlib.ubx_mon_ver import UbxMonVerPoll, UbxMonVer
from ubxlib.ubx_cfg_nmea import UbxCfgNmeaPoll, UbxCfgNmea
from ubxlib.ubx_cfg_rst import UbxCfgRstAction
# from ubxlib.ubx_esf_status import UbxEsfStatusPoll, UbxEsfStatus
#  from ubxlib.ubx_mga_ini_time_utc import UbxMgaIniTimeUtc
# from ubxlib.ubx_cfg_gnss import UbxCfgGnssPoll, UbxCfgGnss
from ubxlib.ubx_cfg_nav5 import UbxCfgNav5Poll, UbxCfgNav5
# from ubxlib.ubx_cfg_esfalg import UbxCfgEsfAlgPoll, UbxCfgEsfAlg
# from ubxlib.ubx_esf_alg import UbxEsfAlgPoll, UbxEsfAlg, UbxEsfResetAlgAction
# from ubxlib.frame import UbxCID


class Gnss(object):
    # Singleton accessor
    instance = None

    def __init__(self):
        super().__init__()

        assert Gnss.instance is None
        Gnss.instance = self

        self.ubx = GnssUBlox('/dev/ttyS3')

        # self.data = dict()
        # TODO: Init from real values
        self.__msg_version = None
        self.__msg_nmea = None
        self.__msg_cfg_nav5 = None

    def setup(self):
        self.ubx.setup()

        # Register the frame types we use
        protocols = [UbxMonVer, UbxCfgNmea, UbxCfgNav5]
        for p in protocols:
            self.ubx.register_frame(p)

        m = UbxMonVerPoll()
        self.__msg_version = self.ubx.poll(m)
        print(self.__msg_version)

        self.__msg_nmea = self.__cfg_nmea()
        print(self.__msg_nmea)
        self.__msg_nmea.f.nmeaVersion = 0x41
        self.ubx.set(self.__msg_nmea)

        self.__msg_cfg_nav5 = self.__cfg_nav5()
        print(self.__msg_cfg_nav5)

    def version(self):
        """
        extension_0: ROM BASE 3.01 (107888)
        extension_1: FWVER=ADR 4.21
        extension_2: PROTVER=19.20
        extension_3: MOD=NEO-M8L-0
        extension_4: FIS=0xEF4015 (100111)
        extension_5: GPS;GLO;GAL;BDS
        extension_6: SBAS;IMES;QZSS
        """
        ver = self.__msg_version
        data = {
            'swVersion': ver.f.swVersion,
            'hwVersion': ver.f.hwVersion,
            'protocol': ver.f.extension_2
        }
        return data

    def nmea_protocol(self):
        self.__msg_nmea = self.__cfg_nmea()
        ver_in_hex = self.__msg_nmea.f.nmeaVersion
        print(ver_in_hex)

        ver = int(ver_in_hex / 16)
        rev = int(ver_in_hex % 16)

        return f'{ver}.{rev}'

    def cold_start(self):
        print('Executing GNSS cold start')

        msg = UbxCfgRstAction()
        msg.cold_start()
        msg.pack()
        self.ubx.send(msg)
        # TODO: Remove .pack as soon as ubxlib implements this internally

        return 'Success'

    def dynamic_model(self):
        self.__msg_cfg_nav5 = self.__cfg_nav5()
        return self.__msg_cfg_nav5.f.dynModel

    def set_dynamic_model(self, dyn_model):
        print(f'Changing dynamic model to {dyn_model}')
        assert(0 <= dyn_model <= 7)

        self.__msg_cfg_nav5 = self.__cfg_nav5()
        print(f'current dyn model: {self.__msg_cfg_nav5.f.dynModel}')
        if dyn_model != self.__msg_cfg_nav5.f.dynModel:
            print('changing')
            self.__msg_cfg_nav5.f.dynModel = dyn_model
            self.ubx.set(self.__msg_cfg_nav5)
            res = 'Success'
        else:
            res = 'Ignored'

    def __cfg_nav5(self):
        msg = UbxCfgNav5Poll()
        res = self.ubx.poll(msg)
        return res

    def __cfg_nmea(self):
        msg = UbxCfgNmeaPoll()
        res = self.ubx.poll(msg)
        return res
