"""
Retrieves and parses the core configuration JSON from speedtest.net.
"""

import json
from collections.abc import Mapping
from dataclasses import replace
from json import JSONDecodeError

import httpx2

from speedtest.exceptions import CLIError
from speedtest.models import ApiConfig
from speedtest.utils import CONFIG_URL, great_circle_km

from .network import build_user_agent

__all__ = ["ConfigFetchError", "fetch_raw_config", "get_config", "parse_config"]


class ConfigFetchError(CLIError):
    """Raised when the configuration cannot be retrieved or parsed."""


def fetch_raw_config(url: str = CONFIG_URL, params: Mapping[str, str | float] | None = None) -> str:
    """
    Fetches the raw JSON string configuration from the Speedtest API.
    This function is strictly I/O bound.
    """

    headers = {
        "User-Agent": build_user_agent(),
        "Accept": "application/json",
    }

    try:
        response = httpx2.get(url, headers=headers, params=params, timeout=10.0)
        response.raise_for_status()

        return response.text

    except httpx2.HTTPStatusError as e:
        raise ConfigFetchError(f"HTTP {e.response.status_code}: Failed to fetch config.") from e

    except httpx2.RequestError as e:
        raise ConfigFetchError(f"Failed to retrieve config from network: {e}") from e


def parse_config(raw_data: str) -> ApiConfig:
    """
    Parses the raw JSON string into strict dataclass models.
    This function is strictly CPU-bound and pure.
    """

    try:
        parsed_dict = json.loads(raw_data)
        return ApiConfig.from_dict(parsed_dict)

    except JSONDecodeError as e:
        raise ConfigFetchError(f"Failed to parse config JSON: {e}") from e

    except Exception as e:
        # Catching generic exceptions from the from_dict factory if data schema changes
        raise ConfigFetchError(f"Failed to map config to domain model: {e}") from e


def get_config(search: str | None = None, location: tuple[float, float] | None = None) -> ApiConfig:
    """
    Orchestrates fetching the raw data and building the strict dataclass models.

    `search` and `location` change which servers speedtest.net returns, not who the client is.
    Server distances are recomputed in km: the API's own value is not reliable.
    """

    params: dict[str, str | float] = {}
    if search:
        params["search"] = search
    if location is not None:
        params["lat"], params["lon"] = location

    raw_data = fetch_raw_config(params=params or None)
    config = parse_config(raw_data)

    origin = location if location is not None else (config.location.latitude, config.location.longitude)
    config.servers = [replace(s, distance=round(great_circle_km(*origin, s.lat, s.lon))) for s in config.servers]

    return config
