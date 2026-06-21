"""
Handles formatting, printing, and JSON output.
"""

import dataclasses

from speedtest.models import TestResult
from speedtest.utils.logger import logger

__all__ = ["convert_speed", "display_results"]


def convert_speed(speed_bps: float, unit_divisor: int) -> float:
    """Convert speed from bits per second to the requested unit (e.g., Mega/s)."""

    return (speed_bps / 1_000_000) / unit_divisor


def display_results(
    results: TestResult,
    units: tuple[str, int],
    share: bool = False,
    json_format: bool = False,
) -> None:
    """Render the final output to the user based on requested format (JSON, Text)."""

    logger.debug(f"Results:\n{dataclasses.asdict(results)!r}")

    unit_name, unit_divisor = units

    if json_format:
        import json

        print(json.dumps(dataclasses.asdict(results)))
        return

    if results.download_bps is not None:
        dl_speed = convert_speed(results.download_bps, unit_divisor)
        print(f"Download: {dl_speed:.2f} M{unit_name}/s")

    if results.upload_bps is not None:
        ul_speed = convert_speed(results.upload_bps, unit_divisor)
        print(f"Upload: {ul_speed:.2f} M{unit_name}/s")

    if share:
        if results.share_url:
            print(f"Share results: {results.share_url}")
        else:
            logger.warning("Share URL generation failed or was not executed.")
