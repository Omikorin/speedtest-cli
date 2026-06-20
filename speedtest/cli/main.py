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
from speedtest.cli.output import display_results
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

    # is_quiet: bool = args.json
    # setup_logging(debug=args.debug, quiet=is_quiet)
    setup_logging(debug=args.debug)

    _validate_args(args)

    # Setup graceful shutdown for threads
    shutdown_event = _register_shutdown_handler()

    threads = (
        1 if args.single else (args.threads if getattr(args, "threads", None) is not None else 4)
    )

    # Initialize Core Pipeline
    logger.info("Retrieving speedtest.net configuration...")

    st = get_speedtest_instance(
        shutdown_event=shutdown_event,
        threads=threads,
        # source=args.source,
        # timeout=args.timeout,
    )

    # Handle early-exit commands
    if args.list:
        return handle_server_list(st)

    # Execute Standard Pipeline
    logger.info(f"Testing from {st.config.isp_name} ({st.config.ip_address})...")

    select_server(st, server=args.server)

    server_cfg = st.results.server
    if not server_cfg:
        return ExitStatus.ERROR

    logger.info(
        f"Hosted by {server_cfg.sponsor} "
        f"({server_cfg.name}) "
        f"[{server_cfg.distance:.2f} km]: {st.results.ping:.4f} ms"
    )

    run_transfer_tests(
        st,
        no_download=args.no_download,
        no_upload=args.no_upload,
        units=args.units,
    )
    display_results(
        results=st.results,
        # json_format=args.json,
        share=args.share,
    )

    return ExitStatus.SUCCESS.value
