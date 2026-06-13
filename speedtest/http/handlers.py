"""
Custom urllib handlers and the OpenerDirector builder
"""

import ssl
from typing import Any
from urllib.request import (
    AbstractHTTPHandler,
    HTTPDefaultErrorHandler,
    HTTPErrorProcessor,
    HTTPRedirectHandler,
    OpenerDirector,
    ProxyHandler,
    Request,
)

from speedtest.http.connections import (
    SpeedtestHTTPConnection,
    SpeedtestHTTPSConnection,
    build_connection,
)
from speedtest.http.request import build_user_agent
from speedtest.utils.logger import logger

__all__ = [
    "SpeedtestHTTPHandler",
    "SpeedtestHTTPSHandler",
    "build_opener",
]


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
            build_connection(
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
            build_connection(
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
