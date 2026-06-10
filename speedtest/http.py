class FakeShutdownEvent(object):
    """Class to fake a threading.Event.is_set so that users of this module
    are not required to register their own threading.Event()
    """

    @staticmethod
    def is_set():
        "Dummy method to always return false" ""
        return False


# Exception "constants" to support Python 2 through Python 3
from http.client import BadStatusLine, HTTPConnection, HTTPSConnection
from io import BytesIO, StringIO
import platform
import socket
import ssl
import threading
import timeit
from urllib.error import HTTPError
from urllib.request import (
    AbstractHTTPHandler,
    HTTPDefaultErrorHandler,
    HTTPErrorProcessor,
    HTTPRedirectHandler,
    OpenerDirector,
    ProxyHandler,
    Request,
    urlopen,
)

from speedtest import __version__
from speedtest.exceptions import (
    SpeedtestCLIError,
    SpeedtestHTTPError,
    SpeedtestUploadTimeout,
)
from speedtest.utils import printer

try:
    CERT_ERROR = (ssl.CertificateError,)
except AttributeError:
    CERT_ERROR = tuple()

HTTP_ERRORS = (HTTPError, socket.error, ssl.SSLError, BadStatusLine) + CERT_ERROR


try:
    import gzip

    GZIP_BASE = gzip.GzipFile
except ImportError:
    gzip = None
    GZIP_BASE = object


class SpeedtestHTTPConnection(HTTPConnection):
    """Custom HTTPConnection to support source_address across
    Python 2.4 - Python 3
    """

    def __init__(self, *args, **kwargs):
        source_address = kwargs.pop("source_address", None)
        timeout = kwargs.pop("timeout", 10)

        self._tunnel_host = None

        HTTPConnection.__init__(self, *args, **kwargs)

        self.source_address = source_address
        self.timeout = timeout

    def connect(self):
        """Connect to the host and port specified in __init__."""
        self.sock = socket.create_connection(
            (self.host, self.port), self.timeout, self.source_address
        )

        if self._tunnel_host:
            self._tunnel()


class SpeedtestHTTPSConnection(HTTPSConnection):
    """Custom HTTPSConnection to support source_address across
    Python 2.4 - Python 3
    """

    default_port = 443

    def __init__(self, *args, **kwargs):
        source_address = kwargs.pop("source_address", None)
        timeout = kwargs.pop("timeout", 10)

        self._tunnel_host = None

        HTTPSConnection.__init__(self, *args, **kwargs)

        self.timeout = timeout
        self.source_address = source_address

    def connect(self):
        "Connect to a host on a given (SSL) port."
        self.sock = socket.create_connection(
            (self.host, self.port), self.timeout, self.source_address
        )

        if self._tunnel_host:
            self._tunnel()

        try:
            kwargs = {}
            if hasattr(ssl, "SSLContext"):
                if self._tunnel_host:
                    kwargs["server_hostname"] = self._tunnel_host
                else:
                    kwargs["server_hostname"] = self.host
            self.sock = self._context.wrap_socket(self.sock, **kwargs)
        except AttributeError:
            self.sock = ssl.wrap_socket(self.sock)
            try:
                self.sock.server_hostname = self.host
            except AttributeError:
                pass


def _build_connection(connection, source_address, timeout, context=None):
    """Cross Python 2.4 - Python 3 callable to build an ``HTTPConnection`` or
    ``HTTPSConnection`` with the args we need

    Called from ``http(s)_open`` methods of ``SpeedtestHTTPHandler`` or
    ``SpeedtestHTTPSHandler``
    """

    def inner(host, **kwargs):
        kwargs.update({"source_address": source_address, "timeout": timeout})
        if context:
            kwargs["context"] = context
        return connection(host, **kwargs)

    return inner


class SpeedtestHTTPHandler(AbstractHTTPHandler):
    """Custom ``HTTPHandler`` that can build a ``HTTPConnection`` with the
    args we need for ``source_address`` and ``timeout``
    """

    def __init__(self, debuglevel=0, source_address=None, timeout=10):
        AbstractHTTPHandler.__init__(self, debuglevel)
        self.source_address = source_address
        self.timeout = timeout

    def http_open(self, req):
        return self.do_open(
            _build_connection(
                SpeedtestHTTPConnection, self.source_address, self.timeout
            ),
            req,
        )

    http_request = AbstractHTTPHandler.do_request_


class SpeedtestHTTPSHandler(AbstractHTTPHandler):
    """Custom ``HTTPSHandler`` that can build a ``HTTPSConnection`` with the
    args we need for ``source_address`` and ``timeout``
    """

    def __init__(self, debuglevel=0, context=None, source_address=None, timeout=10):
        AbstractHTTPHandler.__init__(self, debuglevel)
        self._context = context
        self.source_address = source_address
        self.timeout = timeout

    def https_open(self, req):
        return self.do_open(
            _build_connection(
                SpeedtestHTTPSConnection,
                self.source_address,
                self.timeout,
                context=self._context,
            ),
            req,
        )

    https_request = AbstractHTTPHandler.do_request_


def build_opener(source_address=None, timeout=10):
    """Function similar to ``urllib2.build_opener`` that will build
    an ``OpenerDirector`` with the explicit handlers we want,
    ``source_address`` for binding, ``timeout`` and our custom
    `User-Agent`
    """

    printer("Timeout set to %d" % timeout, debug=True)

    if source_address:
        source_address_tuple = (source_address, 0)
        printer("Binding to source address: %r" % (source_address_tuple,), debug=True)
    else:
        source_address_tuple = None

    handlers = [
        ProxyHandler(),
        SpeedtestHTTPHandler(source_address=source_address_tuple, timeout=timeout),
        SpeedtestHTTPSHandler(source_address=source_address_tuple, timeout=timeout),
        HTTPDefaultErrorHandler(),
        HTTPRedirectHandler(),
        HTTPErrorProcessor(),
    ]

    opener = OpenerDirector()
    opener.addheaders = [("User-agent", build_user_agent())]

    for handler in handlers:
        opener.add_handler(handler)

    return opener


class GzipDecodedResponse(GZIP_BASE):
    """A file-like object to decode a response encoded with the gzip
    method, as described in RFC 1952.

    Largely copied from ``xmlrpclib``/``xmlrpc.client`` and modified
    to work for py2.4-py3
    """

    def __init__(self, response):
        # response doesn't support tell() and read(), required by
        # GzipFile
        if not gzip:
            raise SpeedtestHTTPError(
                "HTTP response body is gzip encoded, "
                "but gzip support is not available"
            )
        IO = BytesIO or StringIO
        self.io = IO()
        while 1:
            chunk = response.read(1024)
            if len(chunk) == 0:
                break
            self.io.write(chunk)
        self.io.seek(0)
        gzip.GzipFile.__init__(self, mode="rb", fileobj=self.io)

    def close(self):
        try:
            gzip.GzipFile.close(self)
        finally:
            self.io.close()


def build_user_agent():
    """Build a Mozilla/5.0 compatible User-Agent string"""

    ua_tuple = (
        "Mozilla/5.0",
        "(%s; U; %s; en-us)" % (platform.platform(), platform.architecture()[0]),
        "Python/%s" % platform.python_version(),
        "(KHTML, like Gecko)",
        "speedtest-cli-ng/%s" % __version__,
    )
    user_agent = " ".join(ua_tuple)
    printer("User-Agent: %s" % user_agent, debug=True)
    return user_agent


def build_request(url, data=None, headers=None, bump="0", secure=False):
    """Build a urllib2 request object

    This function automatically adds a User-Agent header to all requests

    """

    if not headers:
        headers = {}

    if url[0] == ":":
        scheme = ("http", "https")[bool(secure)]
        schemed_url = "%s%s" % (scheme, url)
    else:
        schemed_url = url

    if "?" in url:
        delim = "&"
    else:
        delim = "?"

    # WHO YOU GONNA CALL? CACHE BUSTERS!
    final_url = "%s%sx=%s.%s" % (
        schemed_url,
        delim,
        int(timeit.time.time() * 1000),
        bump,
    )

    headers.update(
        {
            "Cache-Control": "no-cache",
        }
    )

    printer("%s %s" % (("GET", "POST")[bool(data)], final_url), debug=True)

    return Request(final_url, data=data, headers=headers)


def catch_request(request, opener=None):
    """Helper function to catch common exceptions encountered when
    establishing a connection with a HTTP/HTTPS request

    """

    if opener:
        _open = opener.open
    else:
        _open = urlopen

    try:
        uh = _open(request)
        if request.get_full_url() != uh.geturl():
            printer("Redirected to %s" % uh.geturl(), debug=True)
        return uh, False
    except HTTP_ERRORS as e:
        return None, e


def get_response_stream(response):
    """Helper function to return either a Gzip reader if
    ``Content-Encoding`` is ``gzip`` otherwise the response itself

    """

    try:
        getheader = response.headers.getheader
    except AttributeError:
        getheader = response.getheader

    if getheader("content-encoding") == "gzip":
        return GzipDecodedResponse(response)

    return response


class HTTPDownloader(threading.Thread):
    """Thread class for retrieving a URL"""

    def __init__(
        self,
        i,
        request,
        start,
        timeout,
        opener=None,
        shutdown_event: threading.Event | None = None,
    ):
        threading.Thread.__init__(self)
        self.request = request
        self.result = [0]
        self.starttime = start
        self.timeout = timeout
        self.i = i
        if opener:
            self._opener = opener.open
        else:
            self._opener = urlopen

        if shutdown_event:
            self._shutdown_event = shutdown_event
        else:
            self._shutdown_event = FakeShutdownEvent()

    def run(self):
        try:
            if (timeit.default_timer() - self.starttime) <= self.timeout:
                f = self._opener(self.request)
                while (
                    not self._shutdown_event.is_set()
                    and (timeit.default_timer() - self.starttime) <= self.timeout
                ):
                    self.result.append(len(f.read(10240)))
                    if self.result[-1] == 0:
                        break
                f.close()
        except IOError:
            pass
        except HTTP_ERRORS:
            pass


class HTTPUploaderData(object):
    """File like object to improve cutting off the upload once the timeout
    has been reached
    """

    def __init__(self, length, start, timeout, shutdown_event=None):
        self.length = length
        self.start = start
        self.timeout = timeout

        if shutdown_event:
            self._shutdown_event = shutdown_event
        else:
            self._shutdown_event = FakeShutdownEvent()

        self._data = None

        self.total = [0]

    def pre_allocate(self):
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        multiplier = int(round(int(self.length) / 36.0))
        IO = BytesIO or StringIO
        try:
            self._data = IO(
                (
                    "content1=%s" % (chars * multiplier)[0 : int(self.length) - 9]
                ).encode()
            )
        except MemoryError:
            raise SpeedtestCLIError(
                "Insufficient memory to pre-allocate upload data. Please "
                "use --no-pre-allocate"
            )

    @property
    def data(self):
        if not self._data:
            self.pre_allocate()
        return self._data

    def read(self, n=10240):
        if (
            timeit.default_timer() - self.start
        ) <= self.timeout and not self._shutdown_event.is_set():
            chunk = self.data.read(n)
            self.total.append(len(chunk))
            return chunk
        else:
            raise SpeedtestUploadTimeout()

    def __len__(self):
        return self.length


class HTTPUploader(threading.Thread):
    """Thread class for putting a URL"""

    def __init__(
        self,
        i,
        request,
        start,
        size,
        timeout,
        opener=None,
        shutdown_event: threading.Event | None = None,
    ):
        threading.Thread.__init__(self)
        self.request = request
        self.request.data.start = self.starttime = start
        self.size = size
        self.result = 0
        self.timeout = timeout
        self.i = i

        if opener:
            self._opener = opener.open
        else:
            self._opener = urlopen

        if shutdown_event:
            self._shutdown_event = shutdown_event
        else:
            self._shutdown_event = FakeShutdownEvent()

    def run(self):
        request = self.request
        try:
            if (
                timeit.default_timer() - self.starttime
            ) <= self.timeout and not self._shutdown_event.is_set():
                try:
                    f = self._opener(request)
                except TypeError:
                    # PY24 expects a string or buffer
                    # This also causes issues with Ctrl-C, but we will concede
                    # for the moment that Ctrl-C on PY24 isn't immediate
                    request = build_request(
                        self.request.get_full_url(), data=request.data.read(self.size)
                    )
                    f = self._opener(request)
                f.read(11)
                f.close()
                self.result = sum(self.request.data.total)
            else:
                self.result = 0
        except (IOError, SpeedtestUploadTimeout):
            self.result = sum(self.request.data.total)
        except HTTP_ERRORS:
            self.result = 0
