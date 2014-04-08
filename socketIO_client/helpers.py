import logging
import requests
import requests.exceptions
import time

from socketIO_client.exceptions import TimeoutError, ConnectionError

log = logging.getLogger(__name__)


def get_response(request, *args, **kw):
    try:
        response = request(*args, **kw)
    except requests.exceptions.Timeout as e:
        raise TimeoutError(e)
    except requests.exceptions.SSLError as e:
        raise ConnectionError('could not negotiate SSL (%s)' % e)
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(e)

    status = response.status_code

    if 200 != status:
        raise ConnectionError('unexpected status code (%s)' % status)

    return response

