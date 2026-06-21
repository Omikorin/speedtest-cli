"""
Handles formatting, printing, and JSON output.
"""

import dataclasses
import json
import sys
from datetime import UTC, datetime

from speedtest.models import SpeedtestConfig, TestResult
from speedtest.utils.logger import logger

__all__ = ["display_results"]


def display_results(
    results: TestResult,
    units: tuple[str, int],
    share: bool = False,
    json_output: bool = False,
    client_config: SpeedtestConfig | None = None,
) -> None:
    """Orchestrate the final output rendering based on the requested format."""

    logger.debug(f"Results:\n{dataclasses.asdict(results)!r}")

    if json_output:
        _print_json(results, client_config)
    else:
        _print_text(results, units, share)


def _print_json(results: TestResult, client_config) -> None:
    """Construct and print the machine-readable JSON representation."""
    json_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "ping": results.ping_ms,
        "download": results.download_bps,
        "upload": results.upload_bps,
        "bytes_received": results.download_bytes,
        "bytes_sent": results.upload_bytes,
        "share": results.share_url,
        "server": dataclasses.asdict(results.server) if results.server else None,
    }

    if client_config:
        json_data["client"] = {
            "ip": client_config.ip_address,
            "isp": client_config.isp_name,
            "isp_id": client_config.isp_id,
            "location": dataclasses.asdict(client_config.location),
        }

    # Pretty-print for terminals, compact for file redirection/piping
    indent = 2 if sys.stdout.isatty() else None
    print(json.dumps(json_data, indent=indent))


def _convert_speed(speed_bps: float, unit_divisor: int) -> float:
    """Convert speed from bits per second to the requested unit (e.g., Mega/s)."""

    return (speed_bps / 1_000_000) / unit_divisor


def _print_text(results: TestResult, units: tuple[str, int], share: bool) -> None:
    """Format and print the human-readable text representation."""
    unit_name, unit_divisor = units

    if results.download_bps is not None:
        dl_speed = _convert_speed(results.download_bps, unit_divisor)
        print(f"Download: {dl_speed:.2f} M{unit_name}/s")

    if results.upload_bps is not None:
        ul_speed = _convert_speed(results.upload_bps, unit_divisor)
        print(f"Upload: {ul_speed:.2f} M{unit_name}/s")

    if share:
        if results.share_url:
            print(f"Share results: {results.share_url}")
        else:
            logger.warning("Share URL generation failed or was not executed.")
