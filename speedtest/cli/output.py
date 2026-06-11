"""
Handles formatting, printing, and CSV/JSON output
"""

import argparse

from speedtest.results import SpeedtestResults
from speedtest.status import ExitStatus
from speedtest.utils import printer


def convert_speed(speed_bps: float, unit_divisor: int) -> float:
    """Convert speed from bits per second to the requested unit (Mega/s)."""

    return (speed_bps / 1_000_000) / unit_divisor


def csv_header(delimiter: str = ",") -> int:
    """Print the CSV Headers."""

    printer(SpeedtestResults.csv_header(delimiter=delimiter))
    return ExitStatus.SUCCESS


def display_results(
    results: SpeedtestResults, args: argparse.Namespace, machine_format: bool
) -> None:
    """Render the final output to the user based on requested format (JSON, CSV, Text)."""

    printer(f"Results:\n{results.dict()!r}", debug=True)

    # force a share link generation if requested before formatted output
    if not args.simple and args.share:
        results.share()

    if args.simple:
        download_speed = convert_speed(results.download, args.units[1])
        upload_speed = convert_speed(results.upload, args.units[1])
        printer(
            f"Ping: {results.ping:.4f} ms\n"
            f"Download: {download_speed:.2f} M{args.units[0]}/s\n"
            f"Upload: {upload_speed:.2f} M{args.units[0]}/s"
        )
    elif args.csv:
        printer(results.csv(delimiter=args.csv_delimiter))
    elif args.json:
        printer(results.json())

    if args.share and not machine_format:
        printer(f"Share results: {results.share()}")
