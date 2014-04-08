import logging

from socketIO_client.exceptions import SocketIOError
from .jsonp import JSONP
from .ws import WebSocket
from .xhr import XHR

TRANSPORTS = {
    'websocket': WebSocket,
    'xhr-polling': XHR,
    'jsonp-polling': JSONP,
}

TRANSPORT_ORDER = ['websocket', 'xhr-polling', 'jsonp-polling']

log = logging.getLogger(__name__)


def negotiate_transport(client_supported_transports, session, is_secure,
                         base_url, dumps, loads, **kwargs):

    server_supported_transports = session.server_supported_transports

    for supported_transport in client_supported_transports:
        if supported_transport in server_supported_transports:
            log.debug('[transport selected] %s', supported_transport)

            return TRANSPORTS[supported_transport](
                session, is_secure, base_url,
                dumps, loads,
                **kwargs
            )

    raise SocketIOError(' '.join([
        'could not negotiate a transport:',
        'client supports %s but' % ', '.join(client_supported_transports),
        'server supports %s' % ', '.join(server_supported_transports),
    ]))
