"""
Custom HTTP/HTTPS socket connection factories.
"""

import ssl
from collections.abc import Callable
from functools import partial
from http.client import HTTPConnection, HTTPSConnection
from typing import Any

__all__ = ["build_connection"]


def build_connection(
    connection_cls: type[HTTPConnection] | type[HTTPSConnection],
    source_address: tuple[str, int] | None,
    timeout: float,
    context: ssl.SSLContext | None = None,
) -> Callable:
    """
    Returns a factory callable that instantiates HTTPConnection or HTTPSConnection
    with a predefined timeout, source_address, and optional SSL context.

    This is designed to be injected into urllib.request handlers (which expect
    a class or callable to instantiate when opening connections).
    """

    kwargs: dict[str, Any] = {"timeout": timeout}

    if source_address:
        kwargs["source_address"] = source_address

    if context and issubclass(connection_cls, HTTPSConnection):
        kwargs["context"] = context

    return partial(connection_cls, **kwargs)
