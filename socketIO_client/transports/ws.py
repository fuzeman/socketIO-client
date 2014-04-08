import logging
import socket
import websocket

from .base import Base, TIMEOUT
from ..exceptions import ConnectionError, TimeoutError

log = logging.getLogger(__name__)


class WebSocket(Base):
    def __init__(self, socketio, secure, base_url, dumps, loads, **kwargs):
        super(WebSocket, self).__init__(socketio, dumps, loads)

        self._connection = None

        self._url = '%s://%s/websocket/%s' % (
            'wss' if secure else 'ws',
            base_url, socketio.id
        )

    def connect(self):
        try:
            log.debug(self._url)
            self._connection = websocket.create_connection(self._url)
        except websocket.WebSocketConnectionClosedException, e:
            raise ConnectionError(e.message)
        except socket.timeout as e:
            raise ConnectionError(e)
        except socket.error as e:
            raise ConnectionError(e)

        self._connection.settimeout(TIMEOUT)

    @property
    def connected(self):
        return self._connection.connected

    def send(self, packet_text):
        try:
            self._connection.send(packet_text)
        except websocket.WebSocketTimeoutException as e:
            raise TimeoutError('timed out while sending %s (%s)' % (packet_text, e))
        except socket.error as e:
            raise ConnectionError('disconnected while sending %s (%s)' % (packet_text, e))

    def recv(self):
        try:
            yield self._connection.recv()
        except websocket.WebSocketTimeoutException as e:
            raise TimeoutError(e)
        except websocket.SSLError as e:
            raise ConnectionError(e)
        except websocket.WebSocketConnectionClosedException as e:
            raise ConnectionError('connection closed (%s)' % e)
        except socket.error as e:
            raise ConnectionError(e)

    def close(self):
        self._connection.close()
