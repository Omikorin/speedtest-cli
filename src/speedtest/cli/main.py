"""
The main entry point of the CLI shell.
"""

import dataclasses
import signal
import threading
from types import FrameType

from speedtest.client import SpeedtestClient
from speedtest.engine import get_config
from speedtest.exceptions import CLIError
from speedtest.models import RunContext, TestResult
from speedtest.utils import ExitStatus, console, logger, setup_logging

from .display import print_json, print_server_list
from .parser import parse_args

__all__ = ["shell"]


def _register_shutdown_handler() -> threading.Event:
    """Register a SIGINT handler and return the associated shutdown event."""

    shutdown_event = threading.Event()

    def _handler(signum: int, frame: FrameType | None) -> None:
        shutdown_event.set()
        logger.warning("Stopping speedtest-cli...")
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, _handler)
    return shutdown_event


def shell() -> int:
    """Run the full speedtest.net test orchestrator."""

    raw_args = parse_args()
    ctx = RunContext.from_args(raw_args)
    results = TestResult()

    setup_logging(debug=ctx.debug_mode, quiet=ctx.is_quiet)

    ctx.shutdown_event = _register_shutdown_handler()
    client = SpeedtestClient()

    try:
        with console.status("[bold cyan]Retrieving speedtest.net configuration..."):
            ctx.api_config = get_config()

        logger.info(
            f"Client: {ctx.api_config.ip_address} (ISP: {ctx.api_config.isp_name}) "
            f"Location: [{ctx.api_config.location.latitude:.4f}, {ctx.api_config.location.longitude:.4f}]"
        )

        with console.status("[bold cyan]Fetching server list..."):
            target_servers = client.get_target_servers(config=ctx.api_config, target_id=ctx.target_server_id)

        if ctx.list_servers_only:
            return print_server_list(target_servers)

        with console.status("[bold cyan]Selecting best server..."):
            results.server, results.ping_ms = client.select_best_server(target_servers)

        logger.info(
            f"Test server: [{results.server.id}] {results.server.distance} km "
            f"{results.server.name} ({results.server.country}) "
            f"by {results.server.sponsor}"
        )

        logger.info(f"Latency: {results.ping_ms:.5f} ms")

        if not ctx.no_download:
            with console.status("[bold green]Testing download speed..."):
                results.download_bytes, results.download_bps = client.download(server=results.server, ctx=ctx)

            dl_speed = results.get_download_speed(ctx.unit_divisor)
            dl_mb = results.get_downloaded_megabytes()
            if dl_speed is not None and dl_mb is not None:
                logger.info(f"Download: {dl_speed:.2f} M{ctx.unit_name}/s ({dl_mb:.2f} MB)")

        if not ctx.no_upload:
            with console.status("[bold yellow]Testing upload speed..."):
                results.upload_bytes, results.upload_bps = client.upload(server=results.server, ctx=ctx)

            ul_speed = results.get_upload_speed(ctx.unit_divisor)
            ul_mb = results.get_uploaded_megabytes()
            if ul_speed is not None and ul_mb is not None:
                logger.info(f"Upload: {ul_speed:.2f} M{ctx.unit_name}/s ({ul_mb:.2f} MB)")

        if ctx.share:
            with console.status("[bold magenta]Generating share link..."):
                results.share_url = client.generate_share_link(results)

            logger.info(f"Share results: {results.share_url}")

        logger.debug(f"Results:\n{dataclasses.asdict(results)!r}")

        if ctx.json_output:
            print_json(results, ctx.api_config)

    except CLIError as e:
        logger.error(str(e))
        return ExitStatus.ERROR.value

    return ExitStatus.SUCCESS.value
