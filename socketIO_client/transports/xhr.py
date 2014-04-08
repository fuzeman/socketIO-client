import logging
import time

from socketIO_client.helpers import get_response
from socketIO_client.transports.base import Base, TIMEOUT, BOUNDARY

log = logging.getLogger(__name__)


class XHR(Base):

    def __init__(self, socketio, secure, base_url, dumps, loads, **kwargs):
        super(XHR, self).__init__(socketio, dumps, loads)

        self._connected = False

        self._http_session = self._prepare_http_session(kwargs)
        self._url = '%s://%s/xhr-polling/%s' % (
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
        return dict(t=int(time.time()))

    def send(self, packet_text):
        get_response(
            self._http_session.post,
            self._url,
            params=self._params,
            data=packet_text,
            timeout=TIMEOUT
        )

    def recv(self):
        response = get_response(
            self._http_session.get,
            self._url,
            params=self._params,
            timeout=TIMEOUT
        )

        response_text = response.text

        if not response_text.startswith(BOUNDARY):
            yield response_text
            return

        for packet_text in self._yield_text_from_framed_data(response_text):
            yield packet_text

    def close(self):
        get_response(
            self._http_session.get,
            self._url,
            params=dict(self._params.items() + [('disconnect', True)])
        )

        self._connected = False