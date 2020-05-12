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

    def open(self):
        print(f'opening new websocket {self}')
        RealtimeWebSocket.connections.add(self)

        if not RealtimeWebSocket.timer_fn:
            print('Starting new timer')
            RealtimeWebSocket.timer_fn = tornado.ioloop.PeriodicCallback(self.timer, 999)
            RealtimeWebSocket.timer_fn.start()

    def on_close(self):
        print('closing websocket')
        RealtimeWebSocket.connections.remove(self)

    def timer(self):
        RealtimeWebSocket.counter += 1

        m = Model.instance
        gnss = Gnss.instance

        md = m.get_all()

        try:
            rx, tx = md['net-wwan0']['bytes']
            if rx and tx:
                rx_str = f'{int(rx):,}'
                tx_str = f'{int(tx):,}'

            if 'gnss-pos' in md:
                pos = md['gnss-pos']

            esf_status = gnss.esf_status()

            info = {
                'time': RealtimeWebSocket.counter,
                'pos': pos,
                'esf': esf_status,
                'wwan0': {'rx': rx_str, 'tx': tx_str}
            }
            [client.write_message(info) for client in RealtimeWebSocket.connections]

        except KeyError as e:
            print(e)

    # TODO: Add some useful function or remove
    # def on_message(self, message):
    #     print(f'got message: {message}')
