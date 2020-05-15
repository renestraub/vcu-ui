"""
Main Page (Single Page)
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
    connections = set()
    counter = 0
    timer_fn = None

    def __init__(self, application, request, **kwargs):
        print(f'new SimpleWebSocket {self}')
        super().__init__(application, request, **kwargs)
        RealtimeWebSocket.timer_fn = tornado.ioloop.PeriodicCallback(self.timer, 500)

    def open(self):
        print(f'opening new websocket {self}')
        RealtimeWebSocket.connections.add(self)

        if not RealtimeWebSocket.timer_fn.is_running():
            print('Starting timer')
            self.timer()
            RealtimeWebSocket.timer_fn.start()

    def on_close(self):
        print('closing websocket')
        RealtimeWebSocket.connections.remove(self)
        if len(RealtimeWebSocket.connections) == 0:
            print('Stopping timer')
            RealtimeWebSocket.timer_fn.stop()

    def timer(self):
        RealtimeWebSocket.counter += 1

        m = Model.instance
        md = m.get_all()
        gnss = Gnss.instance

        rx, tx = RealtimeWebSocket.safeget((0, 0), md, 'net-wwan0', 'bytes')
        rx_str = f'{int(rx):,}'
        tx_str = f'{int(tx):,}'
        delay_in_ms = RealtimeWebSocket.safeget(0, md, 'link', 'delay') * 1000.0
        wwan0 = {'rx': rx_str, 'tx': tx_str, 'latency': str(delay_in_ms)}

        default = {'fix': '-', 'lon': 0.0, 'lat': 0.0, 'speed': 0.0}
        pos = RealtimeWebSocket.safeget(default, md, 'gnss-pos')

        esf_status = gnss.esf_status()

        info = {
            'time': RealtimeWebSocket.counter,
            'pos': pos,
            'esf': esf_status,
            'wwan0': wwan0,
        }
        [client.write_message(info) for client in RealtimeWebSocket.connections]

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
