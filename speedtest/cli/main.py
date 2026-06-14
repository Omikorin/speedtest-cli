"""
The main entry point of the CLI shell.
"""

import argparse
import signal
import threading
from typing import Any

from speedtest.cli.commands import (
    get_speedtest_instance,
    handle_server_list,
    run_transfer_tests,
    select_server,
)
from speedtest.cli.output import csv_header, display_results
from speedtest.cli.parser import parse_args
from speedtest.exceptions import SpeedtestCLIError
from speedtest.utils.logger import logger, setup_logging
from speedtest.utils.status import ExitStatus

__all__ = ["shell"]


def _register_shutdown_handler() -> threading.Event:
    """Register a SIGINT handler and return the associated shutdown event."""

    shutdown_event = threading.Event()

    def _handler(signum: int, frame: Any) -> None:
        shutdown_event.set()
        logger.warning("\nStopping speedtest-cli...")
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _handler)
    return shutdown_event


def _validate_args(args: argparse.Namespace) -> None:
    """Perform pre-flight validation on CLI arguments."""

    if args.no_download and args.no_upload:
        raise SpeedtestCLIError("Cannot supply both --no-download and --no-upload")


def shell() -> int:
    """Run the full speedtest.net test orchestrator."""

    args = parse_args()

    is_quiet: bool = args.csv or args.json or args.csv_header
    setup_logging(debug=args.debug, quiet=is_quiet)

    _validate_args(args)

    if args.csv_header:
        return csv_header(args.csv_delimiter)

    # Setup graceful shutdown for threads
    shutdown_event = _register_shutdown_handler()

    threads = 1 if args.single else args.threads

    # Initialize Core Pipeline
    logger.info("Retrieving speedtest.net configuration...")

    st = get_speedtest_instance(
        source=args.source,
        timeout=args.timeout,
        threads=threads,
        shutdown_event=shutdown_event,
    )

    # Handle early-exit commands
    if args.list:
        return handle_server_list(st)

    # Execute Standard Pipeline
    client_cfg = st.config.get("client", {})
    logger.info(
        f"Testing from {client_cfg.get('isp', 'Unknown ISP')} "
        f"({client_cfg.get('ip', 'Unknown IP')})..."
    )

    select_server(st, server=args.server)

    server_cfg = st.results.server
    logger.info(
        f"Hosted by {server_cfg.get('sponsor', 'Unknown')} "
        f"({server_cfg.get('name', 'Unknown')}) "
        f"[{server_cfg.get('d', 0.0):.2f} km]: {st.results.ping:.4f} ms"
    )

    run_transfer_tests(
        st,
        no_download=args.no_download,
        no_upload=args.no_upload,
        pre_allocate=not args.no_pre_allocate,
        units=args.units,
    )
    display_results(
        results=st.results,
        csv_format=args.csv,
        json_format=args.json,
        csv_delimiter=args.csv_delimiter,
        share=args.share,
    )

    return ExitStatus.SUCCESS.value
