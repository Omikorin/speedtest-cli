"""
Retrieves and parses the core configuration JSON from speedtest.net.
"""

import json
from json import JSONDecodeError

import httpx2

from speedtest.engine.network import build_user_agent
from speedtest.models import SpeedtestConfig

CONFIG_URL = "https://www.speedtest.net/api/js/config-sdk"

__all__ = ["ConfigFetchError", "fetch_raw_config", "get_config", "parse_config"]


class ConfigFetchError(Exception):
    """Raised when the configuration cannot be retrieved or parsed."""

    pass


def fetch_raw_config(url: str = CONFIG_URL) -> str:
    """
    Fetches the raw JSON string configuration from the Speedtest API.
    This function is strictly I/O bound.
    """

    headers = {
        "User-Agent": build_user_agent(),
        "Accept": "application/json",
    }

    try:
        response = httpx2.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()

        return response.text

    except httpx2.HTTPStatusError as e:
        raise ConfigFetchError(f"HTTP {e.response.status_code}: Failed to fetch config.") from e

    except httpx2.RequestError as e:
        raise ConfigFetchError(f"Failed to retrieve config from network: {e}") from e


def parse_config(raw_data: str) -> SpeedtestConfig:
    """
    Parses the raw JSON string into strict dataclass models.
    This function is strictly CPU-bound and pure.
    """

    try:
        parsed_dict = json.loads(raw_data)
        return SpeedtestConfig.from_dict(parsed_dict)

    except JSONDecodeError as e:
        raise ConfigFetchError(f"Failed to parse config JSON: {e}") from e

    except Exception as e:
        # Catching generic exceptions from the from_dict factory if data schema changes
        raise ConfigFetchError(f"Failed to map config to domain model: {e}") from e


def get_config() -> SpeedtestConfig:
    """
    Orchestrates fetching the raw data and building the strict dataclass models.
    """

    raw_data = fetch_raw_config()
    return parse_config(raw_data)
