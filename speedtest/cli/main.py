"""
The main entry point of the CLI shell.
"""

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
from speedtest.models import RunContext
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


def shell() -> int:
    """Run the full speedtest.net test orchestrator."""

    raw_args = parse_args()
    ctx = RunContext.from_args(raw_args)

    setup_logging(debug=ctx.debug_mode)

    # Setup graceful shutdown for threads
    shutdown_event = _register_shutdown_handler()

    logger.info("Retrieving speedtest.net configuration...")

    st = get_speedtest_instance(
        shutdown_event=shutdown_event,
        threads=ctx.threads,
        # source=args.source,
        # timeout=args.timeout,
    )

    if ctx.list_servers_only:
        return handle_server_list(st)

    logger.info(f"Testing from {st.config.isp_name} ({st.config.ip_address})...")

    select_server(st, server=ctx.target_server_id)

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
        no_download=ctx.no_download,
        no_upload=ctx.no_upload,
        units=ctx.units,
    )
    display_results(
        results=st.results,
        # json_format=args.json,
        share=ctx.share,
    )

    return ExitStatus.SUCCESS.value
