"""
Retrieves and parses the core configuration JSON from speedtest.net.
"""

import json
from json import JSONDecodeError
from urllib.error import URLError
from urllib.request import Request, urlopen

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
    """

    user_agent = build_user_agent()

    req = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})

    try:
        with urlopen(req, timeout=10.0) as response:
            if response.status != 200:
                raise ConfigFetchError(f"HTTP {response.status}: Failed to fetch config.")

            return response.read().decode("utf-8")

    except URLError as e:
        raise ConfigFetchError(f"Failed to retrieve config from network: {e}") from e


def parse_config(raw_data: str) -> SpeedtestConfig:
    """
    Parses the raw JSON string into strict dataclass models.
    """

    try:
        parsed_dict = json.loads(raw_data)
        return SpeedtestConfig.from_dict(parsed_dict)

    except JSONDecodeError as e:
        raise ConfigFetchError(f"Failed to parse config JSON: {e}") from e
    except Exception as e:
        raise ConfigFetchError(f"Failed to map config to domain model: {e}") from e


def get_config() -> SpeedtestConfig:
    """
    Orchestrates fetching the raw data and building the strict dataclass models.
    """

    raw_data = fetch_raw_config()

    return parse_config(raw_data)
