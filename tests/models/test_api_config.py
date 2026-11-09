"""
Tests for the ApiConfig domain model.
"""

from typing import Any

import pytest
from speedtest.models import ApiConfig, Location, Server


def test_api_config_from_dict(raw_api_config: dict[str, Any]) -> None:
    """Test that ApiConfig parses top-level fields and builds real nested models."""

    config = ApiConfig.from_dict(raw_api_config)

    assert config.ip_address == "4.210.177.131"
    assert config.isp_name == "Microsoft Azure"
    assert config.isp_id == 12345
    assert config.guid == "dummy-guid"
    assert config.token == "dummy-token"

    assert isinstance(config.location, Location)
    assert config.location.latitude == pytest.approx(52.3716)
    assert config.location.region_name == "North Holland"

    assert all(isinstance(s, Server) for s in config.servers)
    assert [(s.id, s.sponsor) for s in config.servers] == [(52365, "Odido"), (28922, "PhoenixNAP Global IT Services")]


def test_api_config_isp_id_is_cast_to_int(raw_api_config: dict[str, Any]) -> None:
    raw_api_config["ispId"] = "54321"

    assert ApiConfig.from_dict(raw_api_config).isp_id == 54321


def test_api_config_from_dict_empty_servers(raw_api_config: dict[str, Any]) -> None:
    """Test that a missing servers key defaults to an empty list."""

    del raw_api_config["servers"]

    assert ApiConfig.from_dict(raw_api_config).servers == []


@pytest.mark.parametrize("missing", ["ipAddress", "ispName", "ispId", "guid", "clientAuth", "location"])
def test_api_config_missing_required_key_raises(raw_api_config: dict[str, Any], missing: str) -> None:
    del raw_api_config[missing]

    with pytest.raises(KeyError):
        ApiConfig.from_dict(raw_api_config)


def test_api_config_bad_server_entry_raises(raw_api_config: dict[str, Any]) -> None:
    """One malformed server must not be silently dropped from the list."""

    del raw_api_config["servers"][1]["url"]

    with pytest.raises(KeyError):
        ApiConfig.from_dict(raw_api_config)
