"""
Handles formatting, printing, and CSV/JSON output.
"""

from speedtest.engine.results import SpeedtestResults
from speedtest.utils.logger import logger
from speedtest.utils.status import ExitStatus

__all__ = ["convert_speed", "csv_header", "display_results"]


def convert_speed(speed_bps: float, unit_divisor: int) -> float:
    """Convert speed from bits per second to the requested unit (e.g., Mega/s)."""

    return (speed_bps / 1_000_000) / unit_divisor


def csv_header(delimiter: str = ",") -> int:
    """Print the CSV Headers and return a successful exit status."""

    logger.info(SpeedtestResults.csv_header(delimiter=delimiter))
    return ExitStatus.SUCCESS.value


def display_results(
    results: SpeedtestResults,
    csv_format: bool = False,
    json_format: bool = False,
    csv_delimiter: str = ",",
    share: bool = False,
) -> None:
    """Render the final output to the user based on requested format (JSON, CSV, Text)."""

    logger.debug(f"Results:\n{results.dict()!r}")

    share_link = None
    if share:
        share_link = results.share()

    if csv_format:
        logger.info(results.csv(delimiter=csv_delimiter))
    elif json_format:
        logger.info(results.json())

    if share and not (csv_format or json_format):
        logger.info(f"Share results: {share_link}")
