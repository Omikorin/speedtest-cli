"""
Retrieves and parses the core configuration JSON from speedtest.net.
"""

import json
from json import JSONDecodeError
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from speedtest.http.request import build_user_agent
from speedtest.models import SpeedtestConfig

CONFIG_URL = "https://www.speedtest.net/api/js/config-sdk"


class ConfigFetchError(Exception):
    """Raised when the configuration cannot be retrieved or parsed."""

    pass


def fetch_raw_config(url: str = CONFIG_URL) -> dict[str, Any]:
    """
    Fetches the JSON configuration from the Speedtest API.
    """

    user_agent = build_user_agent()

    req = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json"})

    try:
        with urlopen(req, timeout=10.0) as response:
            if response.status != 200:
                raise ConfigFetchError(f"HTTP {response.status}: Failed to fetch config.")

            body = response.read().decode("utf-8")
            return json.loads(body)

    except (URLError, JSONDecodeError) as e:
        raise ConfigFetchError(f"Failed to retrieve or parse config: {e}") from e


def get_config() -> SpeedtestConfig:
    """
    Orchestrates fetching the raw data and building the strict dataclass models.
    """

    raw_data = fetch_raw_config()
    return SpeedtestConfig.from_dict(raw_data)
