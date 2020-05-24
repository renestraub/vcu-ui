"""
Realtime Display Page

Display speed, gnss fix & esf status and mobile link information
using a websocket
"""
import tornado.web

from vcuui._version import __version__ as version
from vcuui.tools import secs_to_hhmm
from vcuui.data_model import Model
from vcuui.gnss_model import Gnss


class RealtimeHandler(tornado.web.RequestHandler):
    def get(self):
        m = Model.instance
        md = m.get_all()
        serial = md['sys-version']['serial']

        self.render('realtime.html',
                    title=f'VCU Pro ({serial})',
                    version=version
                    )


class RealtimeWebSocket(tornado.websocket.WebSocketHandler):
    instance = None
    connections = set()
    counter = 0
    timer_fn = None
    esf_status = None

    def __init__(self, application, request, **kwargs):
        print(f'new SimpleWebSocket {self}')
        super().__init__(application, request, **kwargs)

        if not RealtimeWebSocket.instance:
            RealtimeWebSocket.instance = self
            RealtimeWebSocket.counter = 0

            print('Starting websocket timer')
            RealtimeWebSocket.timer_fn = tornado.ioloop.PeriodicCallback(RealtimeWebSocket.timer, 900)
            RealtimeWebSocket.timer_fn.start()

    def open(self):
        print(f'adding new connection {self}')
        RealtimeWebSocket.connections.add(self)

    def on_close(self):
        print('closing connection')
        RealtimeWebSocket.connections.remove(self)

    @staticmethod
    def timer():
        m = Model.instance
        md = m.get_all()
        # gnss = Gnss.instance

        rx, tx = RealtimeWebSocket.safeget((0, 0), md, 'net-wwan0', 'bytes')
        delay_in_ms = RealtimeWebSocket.safeget(0, md, 'link', 'delay') * 1000.0
        sq = RealtimeWebSocket.safeget((0, 0), md, 'modem', 'signal-quality')
        wwan0 = {
            'rx': f'{int(rx):,}',
            'tx': f'{int(tx):,}',
            'latency': str(delay_in_ms),
            'signal': str(sq)
        }

        default = {'fix': '-', 'lon': 0.0, 'lat': 0.0, 'speed': 0.0, 'pdop': 99.99}
        pos = RealtimeWebSocket.safeget(default, md, 'gnss-pos')

        gnss_state = RealtimeWebSocket.safeget(None, md, 'gnss-state')
        esf_state = gnss_state['esf-status']

        info = {
            'clients': len(RealtimeWebSocket.connections),
            'time': RealtimeWebSocket.counter,
            'pos': pos,
            'esf': esf_state,
            'wwan0': wwan0,
        }
        [client.write_message(info) for client in RealtimeWebSocket.connections]

        RealtimeWebSocket.counter += 1

    @staticmethod
    def safeget(default, dct, *keys):
        for key in keys:
            try:
                dct = dct[key]
            except KeyError as e:
                print(f'cannot get {e}')
                return default
        return dct

    # TODO: Add some useful function or remove
    # def on_message(self, message):
    #     print(f'got message: {message}')
