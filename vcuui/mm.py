import subprocess


class MM():
    @staticmethod
    def modem():
        id = MM._id()
        if id is not None:
            return Modem(id)

    @staticmethod
    def _id():
        cp = subprocess.run(['mmcli', '-L', '-K'], stdout=subprocess.PIPE)
        res = cp.stdout.decode()
        lines = res.split('\n')
        for l in lines:
            if 'modem-list.value[1]' in l:
                id = MM.last_id(l)
                return int(id)

        return None

    @staticmethod
    def parseline(line):
        t = line.split()
        if len(t) >= 2:
            k = t[0]
            v = t[2]
            return k, v

        return '', ''

    @staticmethod
    def last_id(line):
        id = line[line.rfind('/')+1:]
        return int(id)


class Modem():
    def __init__(self, id):
        self.id = id

    def reset(self):
        subprocess.run(['mmcli', '-m', str(self.id), '-r'],
                       stdout=subprocess.PIPE)

    def setup_signal_query(self):
        subprocess.run(['mmcli', '-m', str(self.id), '--signal-setup', '60'],
                       stdout=subprocess.PIPE)

    def setup_location_query(self):
        subprocess.run(['mmcli', '-m', str(self.id), '--location-enable-3gpp'],
                       stdout=subprocess.PIPE)

    def state(self):
        lines = self._info()
        for l in lines:
            k, v = MM.parseline(l)
            if k == 'modem.generic.state':
                return v

    def signal(self):
        lines = self._info()
        for l in lines:
            k, v = MM.parseline(l)
            if k == 'modem.generic.signal-quality.value':
                return v

    def signal_lte(self):
        rsrp, rsrq = None, None

        lines = self._info('--signal-get')
        for l in lines:
            k, v = MM.parseline(l)
            # print(k, v)
            if k == 'modem.signal.lte.rsrp':
                if v != '--':
                    rsrp = float(v)
            elif k == 'modem.signal.lte.rsrq':
                if v != '--':
                    rsrq = float(v)

        return rsrp, rsrq

    def location(self):
        mcc, mnc, lac, cid = None, None, None, None
        lines = self._info('--location-get')
        for l in lines:
            k, v = MM.parseline(l)
            if k == 'modem.location.3gpp.mcc':
                if v != '--':
                    mcc = int(v)
            if k == 'modem.location.3gpp.mnc':
                if v != '--':
                    mnc = int(v)
            if k == 'modem.location.3gpp.tac':
                if v != '--':
                    lac = int(v, base=16)
            if k == 'modem.location.3gpp.cid':
                if v != '--':
                    cid = int(v, base=16)

        return {'mcc': mcc, 'mnc': mnc, 'lac': lac, 'cid': cid}

    def bearer(self):
        lines = self._info()
        for l in lines:
            k, v = MM.parseline(l)
            if k == 'modem.generic.bearers.value[1]':
                id = MM.last_id(v)
                # print(f'bearer {id}')
                return Bearer(int(id))

        return None

    def _info(self, extra=None):
        cmd = ['mmcli', '-K', '-m', str(self.id)]
        if extra:
            cmd.append(extra)

        # print(cmd)
        cp = subprocess.run(cmd, stdout=subprocess.PIPE)
        res = cp.stdout.decode()
        lines = res.split('\n')
        return lines


class Bearer():
    def __init__(self, id):
        self.id = id

    def uptime(self):
        lines = self._info()
        for l in lines:
            k, v = MM.parseline(l)
            if k == 'bearer.stats.duration':
                if v != '--':
                    return int(v)

    def ip(self):
        lines = self._info()
        for l in lines:
            k, v = MM.parseline(l)
            if k == 'bearer.ipv4-config.address':
                return v

    def _info(self, extra=None):
        cmd = ['mmcli', '-K', '-b', str(self.id)]
        if extra:
            cmd.append(extra)

        # print(cmd)
        cp = subprocess.run(cmd, stdout=subprocess.PIPE)
        res = cp.stdout.decode()
        lines = res.split('\n')
        return lines
