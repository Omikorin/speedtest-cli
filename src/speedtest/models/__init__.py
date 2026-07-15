"""
Domain models and data structures for the speedtest application.
"""

from .api_config import ApiConfig
from .context import RunContext
from .location import Location
from .result import SpeedtestResult
from .server import Server

__all__ = [
    "ApiConfig",
    "Location",
    "RunContext",
    "Server",
    "SpeedtestResult",
]
