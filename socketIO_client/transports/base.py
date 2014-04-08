import logging
import requests
import six
from itertools import izip

from socketIO_client.helpers import retry

log = logging.getLogger(__name__)

TIMEOUT = 3
BOUNDARY = six.u('\ufffd')


class Base(object):
    def __init__(self, socketio, dumps, loads):
        self.socketio = socketio
        self.dumps = dumps
        self.loads = loads

        self._packet_id = 0
        self._callback_by_packet_id = {}
        self._wants_to_disconnect = False
        self._packets = []

    def connect(self):
        raise NotImplementedError()

    @property
    def connected(self):
        raise NotImplementedError()

    def send(self, packet_text):
        raise NotImplementedError()

    def recv(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    def disconnect(self, path=''):
        if not path:
            self._wants_to_disconnect = True

        if not self.connected:
            return

        if path:
            self.send_packet(0, path)
        else:
            self.close()

    def send_connect(self, path):
        self.send_packet(1, path)

    def send_heartbeat(self):
        self.send_packet(2)

    def message(self, path, data, callback):
        if isinstance(data, basestring):
            code = 3
        else:
            code = 4
            data = self.dumps(data, ensure_ascii=False)

        self.send_packet(code, path, data, callback)

    def emit(self, path, event, args, callback):
        data = self.dumps(dict(name=event, args=args), ensure_ascii=False)

        self.send_packet(5, path, data, callback)

    def ack(self, path, packet_id, *args):
        packet_id = packet_id.rstrip('+')

        data = '%s+%s' % (
            packet_id,
            self.dumps(args, ensure_ascii=False),
        ) if args else packet_id

        self.send_packet(6, path, data)

    def noop(self, path=''):
        self.send_packet(8, path)

    def send_packet(self, code, path='', data='', callback=None):
        packet_id = self.set_ack_callback(callback) if callback else ''
        packet_parts = str(code), packet_id, path, data
        packet_text = ':'.join(packet_parts)

        retry(3, self.send, packet_text)
        log.debug('[packet sent] %s', packet_text)

    def recv_packet(self):
        try:
            while self._packets:
                yield self._packets.pop(0)
        except IndexError:
            pass

        for packet_text in self.recv():
            log.debug('[packet received] %s', packet_text)

            try:
                packet_parts = packet_text.split(':', 3)
            except AttributeError:
                log.warn('[packet error] %s', packet_text)
                continue

            code, packet_id, path, data = None, None, None, None
            packet_count = len(packet_parts)

            if 4 == packet_count:
                code, packet_id, path, data = packet_parts
            elif 3 == packet_count:
                code, packet_id, path = packet_parts
            elif 1 == packet_count:
                code = packet_parts[0]

            yield code, packet_id, path, data

    def _enqueue_packet(self, packet):
        self._packets.append(packet)

    def set_ack_callback(self, callback):
        """Set callback to be called after server sends an acknowledgment"""
        self._packet_id += 1
        self._callback_by_packet_id[str(self._packet_id)] = callback

        return '%s+' % self._packet_id

    def get_ack_callback(self, packet_id):
        """Get callback to be called after server sends an acknowledgment"""
        callback = self._callback_by_packet_id[packet_id]
        del self._callback_by_packet_id[packet_id]

        return callback

    @property
    def has_ack_callback(self):
        return True if self._callback_by_packet_id else False

    @staticmethod
    def _yield_text_from_framed_data(framed_data, parse=lambda x: x):
        parts = [parse(x) for x in framed_data.split(BOUNDARY)]

        for text_length, text in izip(parts[1::2], parts[2::2]):
            if text_length != str(len(text)):
                warning = 'invalid declared length=%s for packet_text=%s' % (
                    text_length, text
                )

                log.warn('[packet error] %s', warning)
                continue
            yield text

    @staticmethod
    def _prepare_http_session(kw):
        http_session = requests.Session()
        http_session.headers.update(kw.get('headers', {}))
        http_session.auth = kw.get('auth')
        http_session.proxies.update(kw.get('proxies', {}))
        http_session.hooks.update(kw.get('hooks', {}))
        http_session.params.update(kw.get('params', {}))
        http_session.verify = kw.get('verify')
        http_session.cert = kw.get('cert')
        http_session.cookies.update(kw.get('cookies', {}))
        return http_session
