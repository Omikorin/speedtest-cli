"""
Wraps the core Speedtest logic into CLI actions.
"""

import threading

from speedtest.cli.output import convert_speed
from speedtest.client import Speedtest
from speedtest.exceptions import (
    ConfigRetrievalError,
    NoMatchedServer,
    ServersRetrievalError,
    SpeedtestCLIError,
)
from speedtest.http.errors import HTTP_ERRORS
from speedtest.utils.logger import logger
from speedtest.utils.status import ExitStatus

__all__ = [
    "get_speedtest_instance",
    "handle_server_list",
    "select_server",
    "run_transfer_tests",
]

# Exception groupings for cleaner try/except blocks
CONFIG_EXCEPTIONS = tuple(HTTP_ERRORS) + (ConfigRetrievalError,)
SERVER_EXCEPTIONS = tuple(HTTP_ERRORS) + (ServersRetrievalError,)


def get_speedtest_instance(
    source: str | None,
    timeout: float,
    threads: int | None,
    shutdown_event: threading.Event,
) -> Speedtest:
    """Initialize the Speedtest core and fetch initial configurations."""

    try:
        return Speedtest(
            source_address=source,
            timeout=timeout,
            threads=threads,
            shutdown_event=shutdown_event,
        )
    except CONFIG_EXCEPTIONS as e:
        logger.error("Cannot retrieve speedtest configuration")
        raise SpeedtestCLIError(e) from e


def handle_server_list(st: Speedtest) -> int:
    """Handle the --list argument by printing nearby servers and exiting."""

    try:
        st.get_servers()
    except SERVER_EXCEPTIONS as e:
        logger.error("Cannot retrieve speedtest server list")
        raise SpeedtestCLIError(e) from e

    try:
        for _, servers in sorted(st.servers.items()):
            for server in servers:
                line = (
                    f"{server.get('id', 0):>5}) {server.get('sponsor', 'Unknown')} "
                    f"({server.get('name', 'Unknown')}, {server.get('country', 'Unknown')}) "
                    f"[{server.get('d', 0.0):.2f} km]"
                )
                print(line)
    except BrokenPipeError:
        pass

    return ExitStatus.SUCCESS.value


def select_server(st: Speedtest, server: int | None = None) -> None:
    """Fetch servers and filter down to the best candidate."""

    logger.info("Retrieving speedtest.net server list...")
    try:
        st.get_servers(server=server)
    except NoMatchedServer as e:
        raise e
    except SERVER_EXCEPTIONS as e:
        logger.error("Cannot retrieve speedtest server list")
        raise SpeedtestCLIError(e) from e

    if server is not None:
        logger.info("Retrieving information for the selected server...")
    else:
        logger.info("Selecting best server based on ping...")

    st.get_best_server()


def run_transfer_tests(
    st: Speedtest,
    no_download: bool = False,
    no_upload: bool = False,
    pre_allocate: bool = True,
    units: tuple[str, int] = ("bits", 1),
) -> None:
    """Execute download and upload test sequences."""

    results = st.results
    unit_name, unit_divisor = units

    if no_download:
        logger.info("Skipping download test")
    else:
        logger.info("Testing download speed")
        st.download()
        download_speed = convert_speed(results.download, unit_divisor)
        logger.info(f"Download: {download_speed:.2f} M{unit_name}/s")

    if no_upload:
        logger.info("Skipping upload test")
    else:
        logger.info("Testing upload speed")
        st.upload(pre_allocate=pre_allocate)
        upload_speed = convert_speed(results.upload, unit_divisor)
        logger.info(f"Upload: {upload_speed:.2f} M{unit_name}/s")
