"""
Client library for the speedtest.net API.
"""

from .client import DEFAULT_SERVER_LIMIT, SpeedtestClient
from .config import fetch_raw_config, get_config, parse_config
from .exceptions import (
    ApiError,
    BestServerFailureError,
    ConfigFetchError,
    InvalidServerError,
    NoMatchedServerError,
    ShareError,
    UploadTimeoutError,
)
from .models import ApiConfig, Location, Server, SpeedtestResult

__all__ = [
    "DEFAULT_SERVER_LIMIT",
    "ApiConfig",
    "ApiError",
    "BestServerFailureError",
    "ConfigFetchError",
    "InvalidServerError",
    "Location",
    "NoMatchedServerError",
    "Server",
    "ShareError",
    "SpeedtestClient",
    "SpeedtestResult",
    "UploadTimeoutError",
    "fetch_raw_config",
    "get_config",
    "parse_config",
]
