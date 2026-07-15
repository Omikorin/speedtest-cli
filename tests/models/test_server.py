"""
Tests for the Server domain model.
"""

import pytest
from speedtest.models import Server


def test_server_from_dict_full() -> None:
    """Test that Server correctly parses and casts all dictionary data."""

    raw_api_data = {
        "id": "1234",
        "name": "New York",
        "sponsor": "Acme Corp",
        "country": "United States",
        "cc": "US",
        "host": "speedtest.example.com:8080",
        "url": "http://speedtest.example.com/speedtest/upload.php",
        "lat": "40.7128",
        "lon": "-74.0060",
        "distance": "17",
        "preferred": 1,
        "isp_id": "54321",
        "https_functional": 1,
        "force_ping_select": 1,
    }

    server = Server.from_dict(raw_api_data)

    assert server.name == "New York"
    assert server.sponsor == "Acme Corp"
    assert server.country == "United States"
    assert server.cc == "US"
    assert server.host == "speedtest.example.com:8080"
    assert server.url == "http://speedtest.example.com/speedtest/upload.php"

    assert server.id == 1234
    assert isinstance(server.id, int)

    assert server.lat == pytest.approx(40.7128)
    assert isinstance(server.lat, float)

    assert server.lon == pytest.approx(-74.0060)
    assert isinstance(server.lon, float)

    assert server.distance == 17
    assert isinstance(server.distance, int)

    assert server.isp_id == 54321
    assert isinstance(server.isp_id, int)

    assert server.preferred is True
    assert server.https_functional is True
    assert server.force_ping_select is True


def test_server_from_dict_missing_booleans() -> None:
    """Test that missing optional boolean fields gracefully default to False."""

    raw_api_data = {
        "id": 1234,
        "name": "New York",
        "sponsor": "Acme Corp",
        "country": "United States",
        "cc": "US",
        "host": "speedtest.example.com:8080",
        "url": "http://speedtest.example.com/speedtest/upload.php",
        "lat": 40.7128,
        "lon": -74.0060,
        "distance": 17,
        "isp_id": 54321,
        # preferred, https_functional, and force_ping_select are missing
    }

    server = Server.from_dict(raw_api_data)

    assert server.preferred is False
    assert server.https_functional is False
    assert server.force_ping_select is False
