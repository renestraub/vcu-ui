import logging
import subprocess

logger = logging.getLogger('vcu-ui')


class MM():
    @staticmethod
    def modem():
        id = MM._id()
        if id is not None:
            return Modem(id)

    @staticmethod
    def command(cmd):
        cp = subprocess.run(cmd, stdout=subprocess.PIPE)
        stdout = cp.stdout.decode()
        return MmResult(stdout)

    @staticmethod
    def _id():
        mmr = MM.command(['mmcli', '-K', '-L'])
        return mmr.id('modem-list.value[1]')


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
        subprocess.run(['mmcli', '-m', str(self.id), '-r'],
                       stdout=subprocess.PIPE)

    def setup_signal_query(self):
        subprocess.run(['mmcli', '-m', str(self.id), '--signal-setup', '30'],
                       stdout=subprocess.PIPE)

    def setup_location_query(self):
        subprocess.run(['mmcli', '-m', str(self.id), '--location-enable-3gpp'],
                       stdout=subprocess.PIPE)

    def state(self):
        mmr = self._info()
        return mmr.text('modem.generic.state')

    def access_tech(self):
        mmr = self._info()
        return mmr.text('modem.generic.access-technologies.value[1]')

    def signal(self):
        mmr = self._info()
        return mmr.dec('modem.generic.signal-quality.value')

    def signal_lte(self):
        res = dict()
        mmr = self._info('--signal-get')
        res['rsrp'] = mmr.number('modem.signal.lte.rsrp')
        res['rsrq'] = mmr.number('modem.signal.lte.rsrq')
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
        cmd = ['mmcli', '-K', '-m', str(self.id)]
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
        cmd = ['mmcli', '-K', '-b', str(self.id)]
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
        cmd = ['mmcli', '-K', '-i', str(self.id)]
        return MM.command(cmd)
