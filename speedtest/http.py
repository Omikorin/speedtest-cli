import gzip
import platform
import shutil
import socket
import ssl
import threading
import timeit
from http.client import BadStatusLine, HTTPConnection, HTTPSConnection
from io import BytesIO
from typing import Any, Callable
from urllib.error import HTTPError, URLError
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
    SpeedtestUploadTimeout,
)
from speedtest.utils import printer

# Consolidating errors
HTTP_ERRORS = (
    HTTPError,
    URLError,
    OSError,
    ssl.SSLError,
    BadStatusLine,
    ssl.CertificateError,
)

UPLOAD_ERRORS = HTTP_ERRORS + (SpeedtestUploadTimeout,)


class SpeedtestHTTPConnection(HTTPConnection):
    """Custom HTTPConnection to support source_address routing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.source_address = kwargs.pop("source_address", None)
        self.timeout = kwargs.pop("timeout", 10)
        self._tunnel_host: str | None = None

        super().__init__(*args, **kwargs)

    def connect(self) -> None:
        """Connect to the host and port specified in __init__."""

        self.sock = socket.create_connection(
            (self.host, self.port), self.timeout, self.source_address
        )

        if self._tunnel_host:
            self._tunnel()


class SpeedtestHTTPSConnection(HTTPSConnection):
    """Custom HTTPSConnection to support source_address routing."""

    default_port = 443

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.source_address = kwargs.pop("source_address", None)
        self.timeout = kwargs.pop("timeout", 10)
        self._tunnel_host: str | None = None

        super().__init__(*args, **kwargs)

    def connect(self) -> None:
        """Connect to a host on a given (SSL) port."""

        self.sock = socket.create_connection(
            (self.host, self.port), self.timeout, self.source_address
        )

        if self._tunnel_host:
            self._tunnel()

        kwargs = {
            "server_hostname": self._tunnel_host if self._tunnel_host else self.host
        }

        self.sock = self._context.wrap_socket(self.sock, **kwargs)


def _build_connection(
    connection: type,
    source_address: tuple[str, int] | None,
    timeout: float,
    context: ssl.SSLContext | None = None,
) -> Callable:
    """Callable to build an ``HTTPConnection`` or ``HTTPSConnection``."""

    def inner(host: str, **kwargs: Any) -> Any:
        kwargs.update({"source_address": source_address, "timeout": timeout})
        if context:
            kwargs["context"] = context
        return connection(host, **kwargs)

    return inner


class SpeedtestHTTPHandler(AbstractHTTPHandler):
    """Custom ``HTTPHandler`` that can build a ``HTTPConnection`` with the args we need."""

    def __init__(
        self,
        debuglevel: int = 0,
        source_address: tuple[str, int] | None = None,
        timeout: float = 10,
    ):
        super().__init__(debuglevel)
        self.source_address = source_address
        self.timeout = timeout

    def http_open(self, req: Request) -> Any:
        return self.do_open(
            _build_connection(
                SpeedtestHTTPConnection, self.source_address, self.timeout
            ),
            req,
        )

    http_request = AbstractHTTPHandler.do_request_


class SpeedtestHTTPSHandler(AbstractHTTPHandler):
    """Custom ``HTTPSHandler`` that can build a ``HTTPSConnection`` with the args we need."""

    def __init__(
        self,
        debuglevel: int = 0,
        context: ssl.SSLContext | None = None,
        source_address: tuple[str, int] | None = None,
        timeout: float = 10,
    ):
        super().__init__(debuglevel)
        self._context = context
        self.source_address = source_address
        self.timeout = timeout

    def https_open(self, req: Request) -> Any:
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


def build_opener(
    source_address: str | None = None, timeout: float = 10
) -> OpenerDirector:
    """Build an ``OpenerDirector`` with explicit handlers."""

    printer(f"Timeout set to {timeout}", debug=True)

    source_address_tuple = (source_address, 0) if source_address else None
    if source_address_tuple:
        printer(f"Binding to source address: {source_address_tuple!r}", debug=True)

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


class GzipDecodedResponse(gzip.GzipFile):
    """A file-like object to decode a response encoded with the gzip method."""

    def __init__(self, response: Any):
        self.io = BytesIO()
        shutil.copyfileobj(response, self.io)
        self.io.seek(0)
        super().__init__(mode="rb", fileobj=self.io)

    def close(self) -> None:
        try:
            super().close()
        finally:
            self.io.close()


def build_user_agent() -> str:
    """Build a Mozilla/5.0 compatible User-Agent string."""

    ua_tuple = (
        "Mozilla/5.0",
        f"({platform.platform()}; U; {platform.architecture()[0]}; en-us)",
        f"Python/{platform.python_version()}",
        "(KHTML, like Gecko)",
        f"speedtest-cli-ng/{__version__}",
    )
    user_agent = " ".join(ua_tuple)
    printer(f"User-Agent: {user_agent}", debug=True)
    return user_agent


def build_request(
    url: str,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    bump: str = "0",
    secure: bool = False,
) -> Request:
    """Build a urllib request object."""

    headers = headers or {}

    if url.startswith(":"):
        scheme = "https" if secure else "http"
        schemed_url = f"{scheme}{url}"
    else:
        schemed_url = url

    delim = "&" if "?" in url else "?"

    # Cache buster using current milliseconds
    final_url = f"{schemed_url}{delim}x={int(timeit.time.time() * 1000)}.{bump}"

    headers["Cache-Control"] = "no-cache"

    method_str = "POST" if data else "GET"
    printer(f"{method_str} {final_url}", debug=True)

    return Request(final_url, data=data, headers=headers)


def catch_request(
    request: Request, opener: OpenerDirector | None = None
) -> tuple[Any, Any]:
    """Helper function to catch common exceptions encountered during HTTP/HTTPS requests."""

    _open = opener.open if opener else urlopen

    try:
        uh = _open(request)
        if request.get_full_url() != uh.geturl():
            printer(f"Redirected to {uh.geturl()}", debug=True)
        return uh, False
    except HTTP_ERRORS as e:
        return None, e


def get_response_stream(response: Any) -> Any:
    """Return a Gzip reader if ``Content-Encoding`` is ``gzip``, otherwise the response itself."""

    if response.getheader("content-encoding") == "gzip":
        return GzipDecodedResponse(response)

    return response


class HTTPDownloader(threading.Thread):
    """Thread class for retrieving a URL."""

    def __init__(
        self,
        i: int,
        request: Request,
        start: float,
        timeout: float,
        opener: OpenerDirector | None = None,
        shutdown_event: threading.Event | None = None,
    ):
        super().__init__()
        self.request = request
        self.result = [0]
        self.starttime = start
        self.timeout = timeout
        self.i = i
        self._opener = opener.open if opener else urlopen
        self._shutdown_event = shutdown_event or threading.Event()

    def run(self) -> None:
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
        except HTTP_ERRORS:
            pass


class HTTPUploaderData:
    """File-like object to improve cutting off the upload once the timeout is reached."""

    def __init__(
        self,
        length: int,
        start: float,
        timeout: float,
        shutdown_event: threading.Event | None = None,
    ):
        self.length = length
        self.start = start
        self.timeout = timeout
        self._shutdown_event = shutdown_event or threading.Event()
        self._data: BytesIO | None = None
        self.total = [0]

    def pre_allocate(self) -> None:
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        multiplier = int(round(self.length / 36.0))

        try:
            payload = f"content1={(chars * multiplier)[:self.length - 9]}".encode()
            self._data = BytesIO(payload)
        except MemoryError:
            raise SpeedtestCLIError(
                "Insufficient memory to pre-allocate upload data. Please use --no-pre-allocate"
            )

    @property
    def data(self) -> BytesIO:
        if not self._data:
            self.pre_allocate()
        return self._data  # type: ignore

    def read(self, n: int = 10240) -> bytes:
        if (
            timeit.default_timer() - self.start
        ) <= self.timeout and not self._shutdown_event.is_set():
            chunk = self.data.read(n)
            self.total.append(len(chunk))
            return chunk

        raise SpeedtestUploadTimeout()

    def __len__(self) -> int:
        return self.length


class HTTPUploader(threading.Thread):
    """Thread class for putting a URL."""

    def __init__(
        self,
        i: int,
        request: Request,
        start: float,
        size: int,
        timeout: float,
        opener: OpenerDirector | None = None,
        shutdown_event: threading.Event | None = None,
    ):
        super().__init__()
        self.request = request
        self.request.data.start = self.starttime = start  # type: ignore
        self.size = size
        self.result = 0
        self.timeout = timeout
        self.i = i
        self._opener = opener.open if opener else urlopen
        self._shutdown_event = shutdown_event or threading.Event()

    def run(self) -> None:
        request = self.request
        try:
            if (
                timeit.default_timer() - self.starttime
            ) <= self.timeout and not self._shutdown_event.is_set():
                f = self._opener(request)
                f.read(11)
                f.close()
                self.result = sum(self.request.data.total)  # type: ignore
            else:
                self.result = 0
        except UPLOAD_ERRORS:
            # fallback to the amount of bytes we successfully managed to upload before the crash/timeout
            self.result = sum(self.request.data.total) if hasattr(self.request, "data") else 0  # type: ignore
