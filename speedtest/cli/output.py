"""
Handles formatting, printing, and JSON output.
"""

from speedtest.engine.results import SpeedtestResults
from speedtest.utils.logger import logger

__all__ = ["convert_speed", "display_results"]


def convert_speed(speed_bps: float, unit_divisor: int) -> float:
    """Convert speed from bits per second to the requested unit (e.g., Mega/s)."""

    return (speed_bps / 1_000_000) / unit_divisor


def display_results(
    results: SpeedtestResults,
    json_format: bool = False,
    share: bool = False,
) -> None:
    """Render the final output to the user based on requested format (JSON, Text)."""

    logger.debug(f"Results:\n{results.to_dict()!r}")

    share_link = None
    if share:
        share_link = results.share()

    if json_format:
        print(results.json())

    if share and not (json_format):
        print(f"Share results: {share_link}")
