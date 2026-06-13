"""
Custom HTTP/HTTPS socket connection classes
"""

import socket
import ssl
from collections.abc import Callable
from http.client import HTTPConnection, HTTPSConnection
from typing import Any

__all__ = [
    "SpeedtestHTTPConnection",
    "SpeedtestHTTPSConnection",
    "build_connection",
]


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


def build_connection(
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
