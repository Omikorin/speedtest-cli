"""
The main entry point of shell
"""

import signal
import threading
from typing import Any, Callable

from speedtest.cli.parser import parse_args, validate_optional_args
from speedtest.cli.output import csv_header, display_results
from speedtest.cli.commands import (
    get_speedtest_instance,
    handle_server_list,
    select_server,
    run_transfer_tests,
)
from speedtest.exceptions import SpeedtestCLIError
from speedtest.status import ExitStatus
from speedtest.utils import printer
import speedtest.utils


def ctrl_c(shutdown_event: threading.Event) -> Callable[[int, Any], None]:
    """Catch Ctrl-C key sequence and set a SHUTDOWN_EVENT for our threaded operations."""

    def inner(signum: int, frame: Any) -> None:
        shutdown_event.set()
        printer("\nStopping speedtest-cli...")
        raise KeyboardInterrupt

    return inner


def shell() -> int:
    """Run the full speedtest.net test orchestrator."""

    shutdown_event = threading.Event()
    signal.signal(signal.SIGINT, ctrl_c(shutdown_event))

    args = parse_args()

    # pre-flight checks
    if args.no_download and args.no_upload:
        raise SpeedtestCLIError("Cannot supply both --no-download and --no-upload")

    if len(args.csv_delimiter) != 1:
        raise SpeedtestCLIError("--csv-delimiter must be a single character")

    if args.csv_header:
        return csv_header(args.csv_delimiter)

    validate_optional_args(args)

    if args.debug:
        speedtest.utils.DEBUG = True

    # state variables
    quiet = bool(args.simple or args.csv or args.json)
    machine_format = bool(args.csv or args.json)

    # initialize
    printer("Retrieving speedtest.net configuration...", quiet)
    st = get_speedtest_instance(args)

    if args.list:
        return handle_server_list(st)

    printer(
        f"Testing from {st.config['client']['isp']} ({st.config['client']['ip']})...",
        quiet,
    )

    # select server
    select_server(st, args, quiet)

    results = st.results
    printer(
        f"Hosted by {results.server['sponsor']} ({results.server['name']}) "
        f"[{results.server['d']:.2f} km]: {results.ping:.4f} ms",
        quiet,
    )

    run_transfer_tests(st, args, quiet)

    display_results(results, args, machine_format)

    return ExitStatus.SUCCESS
