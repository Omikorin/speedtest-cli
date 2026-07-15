"""
Tests for the configuration fetching and parsing engine.
"""

import re
from unittest.mock import MagicMock, patch

import httpx2
import pytest
from speedtest.engine.config import (
    ConfigFetchError,
    fetch_raw_config,
    get_config,
    parse_config,
)


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


@patch("speedtest.engine.config.ApiConfig.from_dict")
def test_parse_config_success(mock_from_dict: MagicMock) -> None:
    """Test that valid JSON strings are parsed and mapped to domain models."""

    mock_from_dict.return_value = "MockApiConfigObject"

    valid_json_str = '{"ipAddress": "127.0.0.1"}'

    result = parse_config(valid_json_str)

    assert result == "MockApiConfigObject"
    mock_from_dict.assert_called_once_with({"ipAddress": "127.0.0.1"})


def test_parse_config_json_decode_error() -> None:
    """Test that invalid JSON strings raise a ConfigFetchError."""

    invalid_json_str = "{invalid-json-without-quotes}"

    with pytest.raises(ConfigFetchError, match="Failed to parse config JSON"):
        parse_config(invalid_json_str)


@patch("speedtest.engine.config.ApiConfig.from_dict")
def test_parse_config_mapping_error(mock_from_dict: MagicMock) -> None:
    """Test that domain mapping errors raise a ConfigFetchError."""

    mock_from_dict.side_effect = KeyError("ipAddress")

    valid_json_str = '{"missing_keys": "true"}'

    with pytest.raises(ConfigFetchError, match="Failed to map config to domain model"):
        parse_config(valid_json_str)


@patch("speedtest.engine.config.parse_config")
@patch("speedtest.engine.config.fetch_raw_config")
def test_get_config_orchestration(mock_fetch: MagicMock, mock_parse: MagicMock) -> None:
    """Test that get_config chains fetching and parsing correctly."""

    mock_fetch.return_value = '{"raw": "data"}'
    mock_parse.return_value = "FinalApiConfigObject"

    result = get_config()

    assert result == "FinalApiConfigObject"
    mock_fetch.assert_called_once_with()
    mock_parse.assert_called_once_with('{"raw": "data"}')
