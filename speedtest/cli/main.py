"""
The main entry point of shell
"""

import signal
import threading
from collections.abc import Callable
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


def ctrl_c(shutdown_event: threading.Event) -> Callable[[int, Any], None]:
    """Catch Ctrl-C key sequence and set a SHUTDOWN_EVENT for our threaded operations."""

    def inner(signum: int, frame: Any) -> None:
        shutdown_event.set()
        logger.warning("\nStopping speedtest-cli...")
        raise KeyboardInterrupt

    return inner


def shell() -> int:
    """Run the full speedtest.net test orchestrator."""

    shutdown_event = threading.Event()
    signal.signal(signal.SIGINT, ctrl_c(shutdown_event))

    args = parse_args()
    setup_logging(debug=args.debug)

    # pre-flight checks
    if args.no_download and args.no_upload:
        raise SpeedtestCLIError("Cannot supply both --no-download and --no-upload")

    if len(args.csv_delimiter) != 1:
        raise SpeedtestCLIError("--csv-delimiter must be a single character")

    if args.csv_header:
        return csv_header(args.csv_delimiter)

    threads = 1 if args.single else args.threads

    # initialize
    logger.info("Retrieving speedtest.net configuration...")
    st = get_speedtest_instance(args, threads=threads)

    if args.list:
        return handle_server_list(st)

    logger.info(
        f"Testing from {st.config['client']['isp']} ({st.config['client']['ip']})..."
    )

    # select server
    select_server(st, args)

    results = st.results
    logger.info(
        f"Hosted by {results.server['sponsor']} ({results.server['name']}) "
        f"[{results.server['d']:.2f} km]: {results.ping:.4f} ms"
    )

    run_transfer_tests(st, args)

    display_results(results, args)

    return ExitStatus.SUCCESS
