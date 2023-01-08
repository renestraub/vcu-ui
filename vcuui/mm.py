import logging
import subprocess

logger = logging.getLogger('vcu-ui')

MMCLI_BIN = '/usr/bin/mmcli'


class MM():
    @staticmethod
    def modem():
        id = MM._id()
        if id is not None:
            return Modem(id)    # else None

    @staticmethod
    def command(cmd):
        cp = subprocess.run(cmd, stdout=subprocess.PIPE)
        stdout = cp.stdout.decode()
        return MmResult(stdout)

    @staticmethod
    def _id():
        mmr = MM.command([MMCLI_BIN, '-K', '-L'])
        # Returns number of modems with each modems id.
        #   modem-list.length   : 1
        #   modem-list.value[1] : /org/freedesktop/ModemManager1/Modem/0
        # In case no modem is found returns the following. Note that no .length
        # entry is present
        #   modem-list : 0

        num_modems = mmr.text('modem-list.length')
        if num_modems:
            return mmr.id('modem-list.value[1]')
        else:
            logger.info('no modem(s) found')
            # None


class MmResult():
    def __init__(self, stdout):
        lines = stdout.split('\n')
        self.items = MmResult._to_dict(lines)

    def id(self, name):
        if not self._exists(name):
            logger.info(f'{name} does not exist')
            return None

        line = self.items[name]
        if line:
            id = line[line.rfind('/') + 1:]
            try:
                return int(id)
            except ValueError:
                logger.warning('MmResult::id() value error')
                return None

    def text(self, name):
        if not self._exists(name):
            return None
        val = self.items[name]
        return val

    def dec(self, name):
        if not self._exists(name):
            return None
        # Check for '--'
        val = self.items[name]
        try:
            return int(val)
        except ValueError:
            return None

    def hex(self, name):
        if not self._exists(name):
            return None
        val = self.items[name]
        try:
            return int(val, base=16)
        except ValueError:
            return None

    def number(self, name):
        if not self._exists(name):
            return None
        val = self.items[name]
        try:
            return float(val)
        except ValueError:
            return None

    def _exists(self, name):
        return name in self.items

    @staticmethod
    def _to_dict(lines):
        res = dict()
        for line in lines:
            k, v = MmResult._parseline(line)
            if k:
                res[k] = v

        return res

    @staticmethod
    def _parseline(line):
        """Split modem manager output lines

        Output format is as here
        modem-list.value[1] : /org/freedesktop/ModemManager1/Modem/0
        """
        k, v = None, None
        t = line.split()
        if len(t) >= 1:
            k = t[0]
        if len(t) >= 3:
            v = t[2]

        return k, v


class Modem():
    def __init__(self, id):
        self.id = id

    def reset(self):
        subprocess.run([MMCLI_BIN, '-m', str(self.id), '-r'],
                       stdout=subprocess.PIPE)

    def setup_signal_query(self):
        subprocess.run([MMCLI_BIN, '-m', str(self.id), '--signal-setup', '2'],
                       stdout=subprocess.PIPE)

    def setup_location_query(self):
        subprocess.run([MMCLI_BIN, '-m', str(self.id), '--location-enable-3gpp'],
                       stdout=subprocess.PIPE)

    def vendor(self):
        mmr = self._info()
        return mmr.text('modem.generic.manufacturer')

    def model(self):
        mmr = self._info()
        return mmr.text('modem.generic.model')

    def revision(self):
        mmr = self._info()
        return mmr.text('modem.generic.revision')

    def state(self):
        mmr = self._info()
        return mmr.text('modem.generic.state')

    def access_tech(self):
        mmr = self._info()
        return mmr.text('modem.generic.access-technologies.value[1]')

    def signal(self):
        mmr = self._info()
        return mmr.dec('modem.generic.signal-quality.value')

    # TODO: Add query method to read --signal-get only once
    #       Remember result in object or provide to caller
    #       This avoids calling overhead and ensures consistency

    def signal_access_tech(self):
        # Reads signal information and decodes current RAT from provided values
        # This works around the problem that access_tech() not always matches
        # the RAT of signal()
        #
        # modem.signal.refresh.rate : 2
        # ...
        # modem.signal.gsm.rssi     : --
        # modem.signal.umts.rssi    : --
        # modem.signal.umts.rscp    : --
        # modem.signal.umts.ecio    : --
        # modem.signal.lte.rssi     : --
        # modem.signal.lte.rsrq     : -14.00
        # modem.signal.lte.rsrp     : -90.00
        # modem.signal.lte.snr      : --
        mmr = self._info('--signal-get')
        # print(mmr.items)
        # print(mmr.number('modem.signal.lte.rsrq'))
        # print(mmr.number('modem.signal.umts.ecio'))
        # print(mmr.number('modem.signal.gsm.rssi'))
        if mmr.number('modem.signal.lte.rsrq'):
            return "lte"
        elif mmr.number('modem.signal.umts.ecio'):
            return "umts"
        elif mmr.number('modem.signal.gsm.rssi'):
            return "gsm"
        else:
            return None

    def signal_lte(self):
        res = dict()
        mmr = self._info('--signal-get')
        res['rsrp'] = mmr.number('modem.signal.lte.rsrp')
        res['rsrq'] = mmr.number('modem.signal.lte.rsrq')

        # Some modems also report rssi and s/n, add if present
        rssi = mmr.number('modem.signal.lte.rsrp')
        if rssi:
            res['rssi'] = rssi
        snr = mmr.number('modem.signal.lte.snr')
        if snr:
            res['snr'] = snr

        return res

    def signal_umts(self):
        res = dict()
        mmr = self._info('--signal-get')
        res['rscp'] = mmr.number('modem.signal.umts.rscp')
        res['ecio'] = mmr.number('modem.signal.umts.ecio')
        return res

    def location(self):
        res = dict()
        mmr = self._info('--location-get')
        res['mcc'] = mmr.dec('modem.location.3gpp.mcc')
        res['mnc'] = mmr.dec('modem.location.3gpp.mnc')
        res['lac'] = mmr.hex('modem.location.3gpp.tac')
        res['cid'] = mmr.hex('modem.location.3gpp.cid')
        return res

    def bearer(self):
        mmr = self._info()
        bid = mmr.id('modem.generic.bearers.value[1]')
        if bid is not None:
            return Bearer(int(bid))

    def sim(self):
        mmr = self._info()
        sid = mmr.id('modem.generic.sim')
        if sid is not None:
            return SIM(int(sid))

    def _info(self, extra=None):
        cmd = [MMCLI_BIN, '-K', '-m', str(self.id)]
        if extra:
            cmd.append(extra)

        return MM.command(cmd)


class Bearer():
    def __init__(self, id):
        self.id = id

    def uptime(self):
        mmr = self._info()
        return mmr.dec('bearer.stats.duration')

    def ip(self):
        mmr = self._info()
        return mmr.text('bearer.ipv4-config.address')

    def _info(self):
        cmd = [MMCLI_BIN, '-K', '-b', str(self.id)]
        return MM.command(cmd)


class SIM():
    def __init__(self, id):
        self.id = id

    def imsi(self):
        mmr = self._info()
        return mmr.text('sim.properties.imsi')

    def iccid(self):
        mmr = self._info()
        return mmr.text('sim.properties.iccid')

    def _info(self):
        cmd = [MMCLI_BIN, '-K', '-i', str(self.id)]
        return MM.command(cmd)
