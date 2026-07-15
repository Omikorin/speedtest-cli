"""
Tests for the SpeedtestResult domain model.
"""

import pytest
from speedtest.models import SpeedtestResult


def test_is_complete_property() -> None:
    """Test that a result is only marked complete when all test phases finish."""

    result = SpeedtestResult()

    # Initially, nothing has run
    assert result.is_complete is False

    # Ping completes
    result.ping_ms = 15.0
    assert result.is_complete is False

    # Download completes
    result.download_bps = 50_000_000.0
    assert result.is_complete is False

    # Upload completes
    result.upload_bps = 25_000_000.0
    assert result.is_complete is True

    # Verify that a missing middle step breaks completeness
    result.download_bps = None
    assert result.is_complete is False


def test_download_speed_calculations() -> None:
    """Test that bytes are correctly converted to Megabits/Megabytes per second."""

    result = SpeedtestResult()

    # Let's pretend we downloaded exactly 12,500,000 bytes (12.5 Megabytes or 100 Megabits)
    # over the course of 10 seconds.
    # So the speed is 100 Mbps, or 12.5 MB/s.
    result.download_bytes = 12_500_000
    result.download_bps = 10_000_000.0  # (12,500,000 bytes / 10s) * 8 bits

    # Test bits output (divisor = 1)
    speed_mbps = result.get_download_speed(unit_divisor=1)
    assert speed_mbps == pytest.approx(10.0)  # 10.0 Mbps

    # Test bytes output (divisor = 8)
    speed_mbps_bytes = result.get_download_speed(unit_divisor=8)
    assert speed_mbps_bytes == pytest.approx(1.25)  # 1.25 MB/s

    # Test total megabytes downloaded
    total_mb = result.get_downloaded_megabytes()
    assert total_mb == pytest.approx(12.5)  # 12,500,000 / (1000 * 1000)


def test_upload_speed_calculations() -> None:
    """Test that bytes are correctly converted to Megabits/Megabytes per second."""

    result = SpeedtestResult()

    # Let's pretend we uploaded exactly 12,500,000 bytes (12.5 Megabytes or 100 Megabits)
    # over the course of 10 seconds.
    # So the speed is 100 Mbps, or 12.5 MB/s.
    result.upload_bytes = 12_500_000
    result.upload_bps = 10_000_000.0  # (12,500,000 bytes / 10s) * 8 bits

    # Test bits output (divisor = 1)
    speed_mbps = result.get_upload_speed(unit_divisor=1)
    assert speed_mbps == pytest.approx(10.0)  # 10.0 Mbps

    # Test bytes output (divisor = 8)
    speed_mbps_bytes = result.get_upload_speed(unit_divisor=8)
    assert speed_mbps_bytes == pytest.approx(1.25)  # 1.25 MB/s

    # Test total megabytes uploaded
    total_mb = result.get_uploaded_megabytes()
    assert total_mb == pytest.approx(12.5)  # 12,500,000 / (1000 * 1000)


def test_empty_results_return_none() -> None:
    """Test that math operations safely return None if the test hasn't run."""

    result = SpeedtestResult()

    assert result.get_download_speed(1) is None
    assert result.get_upload_speed(1) is None
    assert result.get_downloaded_megabytes() is None
    assert result.get_uploaded_megabytes() is None
