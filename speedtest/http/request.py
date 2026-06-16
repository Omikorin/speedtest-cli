"""
Request building and execution utilities.
"""

import platform
import time
from collections.abc import Iterable
from functools import cache
from http.client import HTTPResponse
from urllib.request import OpenerDirector, Request, urlopen

from speedtest import __version__
from speedtest.http.errors import HTTP_ERRORS
from speedtest.http.workers import HTTPUploaderData
from speedtest.utils.logger import logger

__all__ = [
    "build_request",
    "build_user_agent",
    "catch_request",
]


@cache
def build_user_agent() -> str:
    """Build and cache a User-Agent string."""

    system = platform.system() or "UnknownOS"
    machine = platform.machine() or "UnknownArch"

    user_agent = (
        f"Mozilla/5.0 ({system}; {machine}) "
        f"Python/{platform.python_version()} "
        f"speedtest-cli/{__version__}"
    )

    logger.debug(f"User-Agent: {user_agent}")
    return user_agent


def build_request(
    url: str,
    data: bytes | Iterable[bytes] | HTTPUploaderData | None = None,
    headers: dict[str, str] | None = None,
    bump: str = "0",
) -> Request:
    """Build a urllib request object."""

    safe_headers = dict(headers) if headers else {}

    delim = "&" if "?" in url else "?"

    # Cache buster using current milliseconds
    final_url = f"{url}{delim}x={int(time.time() * 1000)}.{bump}"

    safe_headers["Cache-Control"] = "no-cache"

    method_str = "POST" if data else "GET"
    logger.debug(f"{method_str} {final_url}")

    return Request(final_url, data=data, headers=safe_headers, method=method_str)


def catch_request(
    request: Request, opener: OpenerDirector | None = None
) -> tuple[HTTPResponse | None, Exception | None]:
    """Helper function to catch common exceptions encountered during HTTP[S] requests."""

    _open = opener.open if opener else urlopen

    try:
        uh: HTTPResponse = _open(request)

        if request.get_full_url() != uh.geturl():
            logger.debug(f"Redirected to {uh.geturl()}")

        return uh, None
    except HTTP_ERRORS as e:
        logger.debug(f"Request failed: {e}")
        return None, e
