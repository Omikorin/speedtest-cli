"""
Domain models and data structures for the speedtest application.
"""

from .config import SpeedtestConfig
from .context import RunContext
from .result import TestResult
from .server import Location, Server

__all__ = [
    "Location",
    "RunContext",
    "Server",
    "SpeedtestConfig",
    "TestResult",
]
