import logging
import threading
import time

from ping3 import ping

logger = logging.getLogger('vcu-ui')


# PING_HOST = '1.1.1.1'
PING_HOST = '46.231.204.136'    # netmodule.com


class Wwan(object):
    # Singleton accessor
    instance = None

    def __init__(self, model):
        super().__init__()

        assert Wwan.instance is None
        Wwan.instance = self

        self.model = model
        self.wwan_thread = GsmWorker(self.model)

    def setup(self):
        self.wwan_thread.setup()


class GsmWorker(threading.Thread):
    def __init__(self, model):
        super().__init__()

        self.model = model
        self.state = 'init'
        self.counter = 0

    def setup(self):
        self.daemon = True
        self.name = 'wwan-worker'
        self.start()

    def run(self):
        logger.info("running wwan thread")
        self.state = 'init'
        self.counter = 0
        link_data = dict()

        while True:
            info = self.model.get('modem')
            if self.state == 'init':
                # check if we have a valid bearer
                try:
                    if info and 'bearer-ip' in info:
                        logger.info('bearer found')
                        self.state = 'connected'
                except KeyError:
                    pass

            elif self.state == 'connected':
                try:
                    if info and 'bearer-ip' not in info:
                        logger.warning('lost IP connection')

                        link_data['delay'] = 0.0
                        self.model.publish('link', link_data)
                        self.state = 'init'
                    else:
                        if self.counter % 5 == 2:
                            try:
                                delay = ping(PING_HOST, timeout=1.0)
                                if delay:
                                    link_data['delay'] = round(float(delay), 3)
                                else:
                                    link_data['delay'] = 0.0

                                self.model.publish('link', link_data)

                            except OSError as e:
                                logger.warning('Captured ping error')
                                logger.warning(e)

                                link_data['delay'] = 0.0
                                self.model.publish('link', link_data)
                                self.state = 'init'
                except KeyError:
                    pass

            self.counter += 1
            time.sleep(1.0)
