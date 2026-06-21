"""
The main entry point of the CLI shell.
"""

import dataclasses
import signal
import threading
from typing import Any

from speedtest.cli.commands import handle_server_list
from speedtest.cli.output import format_json, format_text
from speedtest.cli.parser import parse_args
from speedtest.client import SpeedtestClient
from speedtest.engine.config import get_config
from speedtest.exceptions import SpeedtestCLIError
from speedtest.models import RunContext, TestResult
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
    results = TestResult()

    setup_logging(debug=ctx.debug_mode, quiet=ctx.is_quiet)
    shutdown_event = _register_shutdown_handler()

    client = SpeedtestClient(shutdown_event=shutdown_event)

    try:
        logger.info("Retrieving speedtest.net configuration...")
        ctx.api_config = get_config()

        logger.info(f"Testing from {ctx.api_config.isp_name} ({ctx.api_config.ip_address})...")

        target_servers = client.get_target_servers(
            config=ctx.api_config, target_id=ctx.target_server_id
        )

        if ctx.list_servers_only:
            return handle_server_list(target_servers)

        # Latency test
        results.server, results.ping_ms = client.select_best_server(target_servers)

        logger.info(
            f"Hosted by {results.server.sponsor} "
            f"({results.server.name}) "
            f"[{results.server.distance:.2f} km]: {results.ping_ms:.4f} ms"
        )

        # Transfer tests
        if not ctx.no_download:
            results.download_bytes, results.download_bps = client.download(
                server=results.server, threads=ctx.threads
            )

        if not ctx.no_upload:
            results.upload_bytes, results.upload_bps = client.upload(
                server=results.server, threads=ctx.threads
            )

        if ctx.share:
            logger.info("Generating share link...")
            results.share_url = client.generate_share_link(results)

        logger.debug(f"Results:\n{dataclasses.asdict(results)!r}")

        if ctx.json_output:
            final_output = format_json(results, ctx.api_config)
        else:
            final_output = format_text(results, ctx.units, ctx.share)

        print(final_output)

        return ExitStatus.SUCCESS.value

    except SpeedtestCLIError as e:
        logger.error(f"Test failed: {e}")

        return ExitStatus.ERROR.value
