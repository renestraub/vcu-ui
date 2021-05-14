"""
Traffic Page
"""
import io
import logging
import subprocess

import tornado.web

from vcuui._version import __version__ as version
from vcuui.data_model import Model

logger = logging.getLogger('vcu-ui')


class TrafficHandler(tornado.web.RequestHandler):
    def get(self):
        try:
            tes = list()
            data = dict()

            # General System Information
            m = Model.instance
            md = m.get_all()

            serial = md['sys-version']['serial']

            self.render('traffic.html',
                        title=f'{serial}',
                        table=tes,
                        data=data,
                        message='',
                        version=version)

        except KeyError as e:
            self.render('traffic.html',
                        title='NG800/VCU Pro',
                        message=f'Data lookup error: {e} not found',
                        table=None,
                        data=None,
                        version='n/a')


class TrafficImageHandler(tornado.web.RequestHandler):
    image_options = {
        'daily.png': ['-d'],
        'monthly.png': ['-m'],
        'summary.png': ['-vs']
    }

    def get(self, filename):
        logger.info(f'asking for traffic image {filename}')
        try:
            vnstati_call = ['vnstati', '-o', '-', '--noedge']
            vnstati_call += self.image_options[filename]
            logger.info(vnstati_call)

            cp = subprocess.run(vnstati_call, capture_output=True)
            if cp.returncode == 0:
                s = cp.stdout
                self.set_header('Content-type', 'image/jpeg')
                self.set_header('Content-length', len(s))
                self.write(s)

        except FileNotFoundError:
            logger.info('vnstati not found')
