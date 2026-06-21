"""
Request building and execution utilities.
"""

import platform
from functools import cache

from speedtest import __version__
from speedtest.utils.logger import logger

__all__ = ["build_user_agent"]


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
