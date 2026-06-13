"""
Request building and catching utilities
"""

import platform
import time
from http.client import HTTPResponse
from typing import Any
from urllib.request import OpenerDirector, Request, urlopen

from speedtest import __version__
from speedtest.http.errors import HTTP_ERRORS
from speedtest.utils.logger import logger

__all__ = [
    "build_user_agent",
    "build_request",
    "catch_request",
]


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
