"""
Tests for the configuration fetching and parsing engine.
"""

import json
import re
from typing import Any
from unittest.mock import MagicMock, patch

import httpx2
import pytest
from speedtest.engine.config import (
    ConfigFetchError,
    fetch_raw_config,
    get_config,
    parse_config,
)
from speedtest.exceptions import SpeedtestError
from speedtest.models import ApiConfig
from speedtest.utils import CONFIG_URL


def test_config_fetch_error_is_a_speedtest_error() -> None:
    """main() only turns SpeedtestError into an exit code; anything else is a traceback."""

    assert issubclass(ConfigFetchError, SpeedtestError)


@patch("speedtest.engine.config.httpx2.get")
@patch("speedtest.engine.config.build_user_agent")
def test_fetch_raw_config_success(mock_build_ua: MagicMock, mock_get: MagicMock) -> None:
    """Test that configuration is successfully fetched via HTTP."""

    mock_build_ua.return_value = "MockUserAgent/1.0"

    mock_response = MagicMock()
    mock_response.text = '{"mock": "data"}'
    mock_get.return_value = mock_response

    result = fetch_raw_config("http://example.com")

    assert result == '{"mock": "data"}'

    mock_get.assert_called_once_with(
        "http://example.com",
        headers={
            "User-Agent": "MockUserAgent/1.0",
            "Accept": "application/json",
        },
        timeout=10.0,
    )
    mock_response.raise_for_status.assert_called_once()


@patch("speedtest.engine.config.httpx2.get")
def test_fetch_raw_config_http_status_error(mock_get: MagicMock) -> None:
    """Test that HTTP errors are caught and re-raised as ConfigFetchError."""

    mock_response = MagicMock()
    mock_response.status_code = 403

    mock_get.side_effect = httpx2.HTTPStatusError(message="Forbidden", request=MagicMock(), response=mock_response)

    with pytest.raises(ConfigFetchError, match=re.escape("HTTP 403: Failed to fetch config.")):
        fetch_raw_config()


@patch("speedtest.engine.config.httpx2.get")
def test_fetch_raw_config_request_error(mock_get: MagicMock) -> None:
    """Test that general network errors are caught and re-raised as ConfigFetchError."""

    mock_get.side_effect = httpx2.RequestError(message="Network Unreachable", request=MagicMock())

    with pytest.raises(ConfigFetchError, match="Failed to retrieve config from network: Network Unreachable"):
        fetch_raw_config()


def test_parse_config_success(raw_api_config: dict[str, Any]) -> None:
    """Test that a realistic payload is parsed into real domain models."""

    config = parse_config(json.dumps(raw_api_config))

    assert isinstance(config, ApiConfig)
    assert config.ip_address == "4.210.177.131"
    assert config.token == "dummy-token"
    assert config.location.city_name == "Amsterdam"
    assert [s.id for s in config.servers] == [52365, 28922]


def test_parse_config_json_decode_error() -> None:
    """Test that invalid JSON strings raise a ConfigFetchError."""

    invalid_json_str = "{invalid-json-without-quotes}"

    with pytest.raises(ConfigFetchError, match="Failed to parse config JSON"):
        parse_config(invalid_json_str)


def test_parse_config_mapping_error() -> None:
    """Test that valid JSON with the wrong shape raises a ConfigFetchError."""

    with pytest.raises(ConfigFetchError, match="Failed to map config to domain model"):
        parse_config('{"missing_keys": "true"}')


def test_parse_config_missing_auth_token(raw_api_config: dict[str, Any]) -> None:
    raw_api_config["clientAuth"] = {}
    raw_json = json.dumps(raw_api_config)

    with pytest.raises(ConfigFetchError, match="Failed to map config to domain model"):
        parse_config(raw_json)


@patch("speedtest.engine.config.httpx2.get")
def test_get_config_fetches_and_parses(mock_get: MagicMock, raw_api_config: dict[str, Any]) -> None:
    """Test the whole path: HTTP response body in, domain model out."""

    mock_get.return_value = httpx2.Response(200, json=raw_api_config, request=httpx2.Request("GET", CONFIG_URL))

    config = get_config()

    assert mock_get.call_args.args[0] == CONFIG_URL
    assert config.guid == "dummy-guid"
    assert len(config.servers) == 2


@patch("speedtest.engine.config.httpx2.get")
def test_get_config_blocked_by_cdn_raises_config_error(mock_get: MagicMock) -> None:
    """Cloudflare answers 403 to unknown clients; that must surface as ConfigFetchError."""

    mock_get.return_value = httpx2.Response(403, text="403 Forbidden", request=httpx2.Request("GET", CONFIG_URL))

    with pytest.raises(ConfigFetchError, match="HTTP 403"):
        get_config()
