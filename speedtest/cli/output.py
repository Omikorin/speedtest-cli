"""
Handles formatting, printing, and CSV/JSON output
"""

import argparse

from speedtest.logger import logger
from speedtest.results import SpeedtestResults
from speedtest.status import ExitStatus

__all__ = ["convert_speed", "csv_header", "display_results"]


def convert_speed(speed_bps: float, unit_divisor: int) -> float:
    """Convert speed from bits per second to the requested unit (Mega/s)."""

    return (speed_bps / 1_000_000) / unit_divisor


def csv_header(delimiter: str = ",") -> int:
    """Print the CSV Headers."""

    logger.info(SpeedtestResults.csv_header(delimiter=delimiter))
    return ExitStatus.SUCCESS


def display_results(results: SpeedtestResults, args: argparse.Namespace) -> None:
    """Render the final output to the user based on requested format (JSON, CSV, Text)."""

    logger.debug(f"Results:\n{results.dict()!r}")

    # force a share link generation if requested before formatted output
    if args.share:
        results.share()

    if args.csv:
        logger.info(results.csv(delimiter=args.csv_delimiter))
    elif args.json:
        logger.info(results.json())

    if args.share and not (args.csv or args.json):
        logger.info(f"Share results: {results.share()}")
