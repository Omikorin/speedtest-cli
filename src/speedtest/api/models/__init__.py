"""
Data structures returned and produced by the speedtest.net API.
"""

from .api_config import ApiConfig
from .location import Location
from .result import SpeedtestResult
from .server import Server

__all__ = [
    "ApiConfig",
    "Location",
    "Server",
    "SpeedtestResult",
]
