"""
Custom urllib handlers and the OpenerDirector builder.
"""

import ssl
from http.client import HTTPConnection, HTTPSConnection
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
from urllib.request import (
    build_opener as std_build_opener,
)

from speedtest.http.connections import build_connection
from speedtest.http.request import build_user_agent

__all__ = [
    "SpeedtestHTTPHandler",
    "SpeedtestHTTPSHandler",
    "build_opener",
]


class SpeedtestHTTPHandler(AbstractHTTPHandler):
    """Custom ``HTTPHandler`` that injects source_address and timeout into connections."""

    def __init__(
        self,
        debuglevel: int = 0,
    ):
        super().__init__(debuglevel)

    def http_open(self, req: Request) -> Any:
        return self.do_open(
            build_connection(HTTPConnection),
            req,
        )

    http_request = AbstractHTTPHandler.do_request_


class SpeedtestHTTPSHandler(AbstractHTTPHandler):
    """Custom ``HTTPSHandler`` that injects source_address, timeout, and SSL context."""

    def __init__(
        self,
        debuglevel: int = 0,
        context: ssl.SSLContext | None = None,
    ):
        super().__init__(debuglevel)

        self._context = context or ssl.create_default_context()

    def https_open(self, req: Request) -> Any:
        return self.do_open(
            build_connection(
                HTTPSConnection,
                context=self._context,
            ),
            req,
        )

    https_request = AbstractHTTPHandler.do_request_


def build_opener() -> OpenerDirector:
    """Build an ``OpenerDirector`` with explicit custom handlers."""

    handlers = [
        ProxyHandler(),
        SpeedtestHTTPHandler(),
        SpeedtestHTTPSHandler(),
        HTTPDefaultErrorHandler(),
        HTTPRedirectHandler(),
        HTTPErrorProcessor(),
    ]

    opener = std_build_opener(*handlers)
    opener.addheaders = [("User-agent", build_user_agent())]

    return opener
