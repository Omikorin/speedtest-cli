import gzip
import platform
import shutil
import socket
import ssl
import threading
import time
from collections.abc import Callable
from http.client import BadStatusLine, HTTPConnection, HTTPResponse, HTTPSConnection
from io import BytesIO
from typing import Any
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
from speedtest.exceptions import SpeedtestCLIError, SpeedtestUploadTimeout
from speedtest.logger import logger

# --- Constants ---
CHUNK_SIZE_BYTES = 10240
PAYLOAD_MULTIPLIER = 36.0
UPLOAD_RESPONSE_TRUNCATION = 11

# Consolidating errors (OSError inherently covers socket.error and IOError)
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
        """Connect to a host on a given SSL port."""

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

    logger.debug(f"Timeout set to {timeout}")

    source_address_tuple = (source_address, 0) if source_address else None
    if source_address_tuple:
        logger.debug(f"Binding to source address: {source_address_tuple!r}")

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
    logger.debug(f"User-Agent: {user_agent}")
    return user_agent


def build_request(
    url: str,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    bump: str = "0",
) -> Request:
    """Build a urllib request object."""

    headers = headers or {}

    delim = "&" if "?" in url else "?"

    # Cache buster using current milliseconds
    final_url = f"{url}{delim}x={int(time.time() * 1000)}.{bump}"

    headers["Cache-Control"] = "no-cache"

    method_str = "POST" if data else "GET"
    logger.debug(f"{method_str} {final_url}")

    return Request(final_url, data=data, headers=headers)


def catch_request(
    request: Request, opener: OpenerDirector | None = None
) -> tuple[Any, Any]:
    """Helper function to catch common exceptions encountered during HTTP[S] requests."""

    _open = opener.open if opener else urlopen

    try:
        uh: HTTPResponse = _open(request)

        if request.get_full_url() != uh.geturl():
            logger.debug(f"Redirected to {uh.geturl()}")
        return uh, False
    except HTTP_ERRORS as e:
        return None, e


def get_response_stream(response: HTTPResponse) -> HTTPResponse | GzipDecodedResponse:
    """Return a Gzip reader if ``Content-Encoding`` is ``gzip``, otherwise the response itself."""

    if response.getheader("content-encoding") == "gzip":
        return GzipDecodedResponse(response)

    return response


def download_worker(
    request: Request,
    start_time: float,
    timeout: float,
    opener: OpenerDirector | None = None,
    shutdown_event: threading.Event | None = None,
) -> int:
    """Worker function for retrieving a URL, returning total bytes downloaded."""

    _opener = opener.open if opener else urlopen
    _shutdown_event = shutdown_event or threading.Event()
    total_downloaded = 0

    try:
        if (time.monotonic() - start_time) <= timeout:
            with _opener(request) as response:
                while (
                    not _shutdown_event.is_set()
                    and (time.monotonic() - start_time) <= timeout
                ):
                    chunk = response.read(CHUNK_SIZE_BYTES)
                    if not chunk:
                        break

                    total_downloaded += len(chunk)
    except HTTP_ERRORS:
        pass

    return total_downloaded


class HTTPUploaderData:
    """File-like object to cleanly truncate the upload once the timeout is reached."""

    def __init__(
        self,
        length: int,
        start_time: float,
        timeout: float,
        shutdown_event: threading.Event | None = None,
    ):
        self.length = length
        self.start_time = start_time
        self.timeout = timeout
        self._shutdown_event = shutdown_event or threading.Event()
        self._data: BytesIO | None = None

        self.total_bytes_read = 0

    def pre_allocate(self) -> None:
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        multiplier = int(round(self.length / PAYLOAD_MULTIPLIER))

        try:
            payload = f"content1={(chars * multiplier)[: self.length - 9]}".encode()
            self._data = BytesIO(payload)
        except MemoryError:
            raise SpeedtestCLIError(
                "Insufficient memory to pre-allocate upload data. Please use --no-pre-allocate"
            )

    @property
    def data(self) -> BytesIO:
        if not self._data:
            self.pre_allocate()
        return self._data

    def read(self, n: int = CHUNK_SIZE_BYTES) -> bytes:
        if (
            time.monotonic() - self.start_time
        ) <= self.timeout and not self._shutdown_event.is_set():
            chunk = self.data.read(n)
            self.total_bytes_read += len(chunk)
            return chunk

        raise SpeedtestUploadTimeout()

    def __len__(self) -> int:
        return self.length


def upload_worker(
    request: Request,
    payload_data: HTTPUploaderData,
    timeout: float,
    opener: OpenerDirector | None = None,
    shutdown_event: threading.Event | None = None,
) -> int:
    """Worker function for putting a URL, returning total bytes uploaded."""

    _opener = opener.open if opener else urlopen
    _shutdown_event = shutdown_event or threading.Event()

    request.data = payload_data

    try:
        if (
            time.monotonic() - payload_data.start_time
        ) <= timeout and not _shutdown_event.is_set():
            with _opener(request) as response:
                response.read(UPLOAD_RESPONSE_TRUNCATION)
            return payload_data.total_bytes_read
        return 0
    except UPLOAD_ERRORS:
        # Fallback to the amount of bytes we successfully managed to upload before crash/timeout
        return payload_data.total_bytes_read
