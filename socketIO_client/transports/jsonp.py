import logging
import re
import requests
import time

from socketIO_client.helpers import get_response
from socketIO_client.transports.base import Base, TIMEOUT, BOUNDARY

log = logging.getLogger(__name__)


class JSONP(Base):

    RESPONSE_PATTERN = re.compile(r'io.j\[(\d+)\]\("(.*)"\);')

    def __init__(self, socketio, secure, base_url, dumps, loads, **kwargs):
        super(JSONP, self).__init__(socketio, dumps, loads)

        self._connected = False
        self._id = 0

        self._http_session = self._prepare_http_session(kwargs)
        self._url = '%s://%s/jsonp-polling/%s' % (
            'https' if secure else 'http',
            base_url, socketio.id
        )

    def connect(self):
        # Create connection
        for packet in self.recv_packet():
            self._enqueue_packet(packet)

        self._connected = True

    @property
    def connected(self):
        return self._connected

    @property
    def _params(self):
        return dict(t=int(time.time()), i=self._id)

    def send(self, packet_text):
        get_response(
            self._http_session.post,
            self._url,
            params=self._params,
            data='d=%s' % requests.utils.quote(self.dumps(packet_text)),
            headers={'content-type': 'application/x-www-form-urlencoded'},
            timeout=TIMEOUT
        )

    def recv(self):
        """Decode the JavaScript response so that we can parse it as JSON"""
        response = get_response(
            self._http_session.get,
            self._url,
            params=self._params,
            headers={'content-type': 'text/javascript; charset=UTF-8'},
            timeout=TIMEOUT
        )

        response_text = response.text

        try:
            self._id, response_text = self.RESPONSE_PATTERN.match(
                response_text).groups()
        except AttributeError:
            log.warn('[packet error] %s', response_text)
            return

        if not response_text.startswith(BOUNDARY):
            yield response_text.decode('unicode_escape')
            return

        for packet_text in self._yield_text_from_framed_data(
                response_text, parse=lambda x: x.decode('unicode_escape')):
            yield packet_text

    def close(self):
        get_response(
            self._http_session.get,
            self._url,
            params=dict(self._params.items() + [('disconnect', True)])
        )

        self._connected = False