"""
Domain models and data structures for the speedtest application.
"""

from .api_config import ApiConfig
from .context import RunContext
from .result import TestResult
from .server import Location, Server

__all__ = [
    "ApiConfig",
    "Location",
    "RunContext",
    "Server",
    "TestResult",
]
