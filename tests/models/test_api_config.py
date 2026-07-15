"""
Tests for the ApiConfig domain model.
"""

from unittest.mock import MagicMock, patch

from speedtest.models import ApiConfig, Location, Server


@patch.object(Location, "from_dict")
@patch.object(Server, "from_dict")
def test_api_config_from_dict(mock_server_from_dict: MagicMock, mock_location_from_dict: MagicMock) -> None:
    """Test that ApiConfig correctly parses top-level fields and delegates nested ones."""

    mock_location_from_dict.return_value = "MockLocationObject"
    mock_server_from_dict.side_effect = ["MockServer1", "MockServer2"]

    raw_api_data = {
        "ipAddress": "1.1.1.1",
        "ispName": "Acme Internet",
        "ispId": "54321",
        "guid": "dummy-guid",
        "clientAuth": {"token": "dummy-token"},
        "location": {"mock": "location_data"},
        "servers": [{"mock": "server_1"}, {"mock": "server_2"}],
    }

    config = ApiConfig.from_dict(raw_api_data)

    assert config.ip_address == "1.1.1.1"
    assert config.isp_name == "Acme Internet"
    assert config.isp_id == 54321
    assert config.guid == "dummy-guid"
    assert config.token == "dummy-token"

    assert config.location == "MockLocationObject"
    mock_location_from_dict.assert_called_once_with({"mock": "location_data"})

    assert config.servers == ["MockServer1", "MockServer2"]
    assert mock_server_from_dict.call_count == 2
    mock_server_from_dict.assert_any_call({"mock": "server_1"})
    mock_server_from_dict.assert_any_call({"mock": "server_2"})


@patch.object(Location, "from_dict")
@patch.object(Server, "from_dict")
def test_api_config_from_dict_empty_servers(
    mock_server_from_dict: MagicMock, mock_location_from_dict: MagicMock
) -> None:
    """Test that ApiConfig handles missing servers gracefully by defaulting to an empty list."""

    mock_location_from_dict.return_value = "MockLocationObject"

    raw_api_data = {
        "ipAddress": "1.1.1.1",
        "ispName": "Acme Internet",
        "ispId": "54321",
        "guid": "dummy-guid",
        "clientAuth": {"token": "dummy-token"},
        "location": {"mock": "location_data"},
    }

    config = ApiConfig.from_dict(raw_api_data)

    assert config.servers == []
    mock_server_from_dict.assert_not_called()
