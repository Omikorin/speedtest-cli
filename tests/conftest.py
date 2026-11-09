"""
Shared fixtures for all pytest suites.
"""

import logging
from collections.abc import Iterator
from typing import Any

import pytest
from speedtest.models import ApiConfig, Location, RunContext, Server, SpeedtestResult
from speedtest.utils import console, logger


@pytest.fixture(autouse=True)
def _reset_logging() -> Iterator[None]:
    """setup_logging mutates global state; undo it so tests stay independent."""

    yield
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    console.quiet = False


@pytest.fixture
def raw_api_config() -> dict[str, Any]:
    """A config-sdk payload shaped like the real API response."""

    def server(server_id: str, sponsor: str, host: str, distance: int) -> dict[str, Any]:
        return {
            "id": server_id,
            "name": "Amsterdam",
            "sponsor": sponsor,
            "country": "Netherlands",
            "cc": "NL",
            "host": host,
            "url": f"http://{host}/speedtest/upload.php",
            "lat": "52.3702",
            "lon": "4.8952",
            "distance": distance,
            "preferred": 0,
            "isp_id": "12345",
            "https_functional": 1,
            "force_ping_select": 0,
        }

    return {
        "ipAddress": "4.210.177.131",
        "ispName": "Microsoft Azure",
        "ispId": 12345,
        "guid": "dummy-guid",
        "clientAuth": {"token": "dummy-token"},
        "location": {
            "latitude": 52.3716,
            "longitude": 4.8883,
            "cityName": "Amsterdam",
            "countryCode": "NL",
            "countryName": "Netherlands",
            "regionCode": "NH",
            "regionName": "North Holland",
        },
        "servers": [
            server("52365", "Odido", "speedtest.odido.example:8080", 1),
            server("28922", "PhoenixNAP Global IT Services", "speedtest.phoenixnap.example:8080", 0),
        ],
    }


@pytest.fixture
def mock_api_config(mock_location: Location) -> ApiConfig:
    """Provides a standard dummy API configuration."""

    return ApiConfig(
        ip_address="1.1.1.1",
        isp_name="Acme Internet",
        isp_id=54321,
        location=mock_location,
        guid="dummy-guid",
        token="dummy-token",
        servers=[],
    )


@pytest.fixture
def mock_location() -> Location:
    return Location(
        latitude=40.0,
        longitude=-74.0,
        city_name="New York",
        country_code="US",
        country_name="United States",
        region_code="NY",
        region_name="New York",
    )


@pytest.fixture
def mock_server() -> Server:
    """Provides a standard dummy server for testing."""

    return Server(
        id=1234,
        name="New York",
        sponsor="Acme Corp",
        country="United States",
        cc="US",
        host="speedtest.example.com:8080",
        url="http://speedtest.example.com/speedtest/upload.php",
        lat=40.7128,
        lon=-74.0060,
        distance=17,
        preferred=False,
        isp_id=54321,
        https_functional=True,
        force_ping_select=False,
    )


@pytest.fixture
def mock_result(mock_server: Server) -> SpeedtestResult:
    return SpeedtestResult(
        server=mock_server,
        ping_ms=15.5,
        download_bps=100_000_000.0,
        upload_bps=50_000_000.0,
        download_bytes=12_500_000,
        upload_bytes=6_250_000,
        share_url="http://speedtest.example.com/result/123",
    )


@pytest.fixture
def mock_run_context() -> RunContext:
    """Provides a dummy execution context."""

    return RunContext(
        list_servers_only=False,
        debug_mode=False,
        is_quiet=False,
        target_server_id=None,
        no_download=False,
        no_upload=False,
        threads=4,
        share=False,
        json_output=False,
        unit_name="b",
        unit_divisor=1,
    )
