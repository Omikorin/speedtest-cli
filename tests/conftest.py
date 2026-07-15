"""
Shared fixtures for all pytest suites.
"""

import pytest
from speedtest.models import ApiConfig, Location, RunContext, Server
from speedtest.models import TestResult as SpeedtestResult


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
        url="http://speedtest.example.com/speedtest/upload.php",
        lat=40.7128,
        lon=-74.0060,
        name="New York",
        country="United States",
        cc="US",
        sponsor="Acme Corp",
        id=1234,
        host="speedtest.example.com:8080",
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
