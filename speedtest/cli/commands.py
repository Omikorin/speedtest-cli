"""
Wraps the core Speedtest logic into CLI actions
"""

import argparse
import errno

from speedtest.cli.output import convert_speed
from speedtest.core import Speedtest
from speedtest.exceptions import (
    ConfigRetrievalError,
    InvalidServerIDType,
    NoMatchedServers,
    ServersRetrievalError,
    SpeedtestCLIError,
)
from speedtest.http import HTTP_ERRORS
from speedtest.logger import logger
from speedtest.status import ExitStatus

__all__ = [
    "get_speedtest_instance",
    "handle_server_list",
    "select_server",
    "run_transfer_tests",
]


# Exception groupings for cleaner try/except blocks
CONFIG_EXCEPTIONS = tuple(HTTP_ERRORS) + (ConfigRetrievalError,)
SERVER_EXCEPTIONS = tuple(HTTP_ERRORS) + (ServersRetrievalError,)


def get_speedtest_instance(args: argparse.Namespace) -> Speedtest:
    """Initialize the Speedtest core and fetch initial configurations."""

    try:
        return Speedtest(source_address=args.source, timeout=args.timeout)
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

    for _, servers in sorted(st.servers.items()):
        for server in servers:
            line = f"{server['id']:>5}) {server['sponsor']} ({server['name']}, {server['country']}) [{server['d']:.2f} km]"
            try:
                logger.info(line)
            except IOError as e:
                if e.errno != errno.EPIPE:
                    raise

    return ExitStatus.SUCCESS


def select_server(st: Speedtest, args: argparse.Namespace) -> None:
    """Fetch servers and filter down to the best candidate."""

    logger.info("Retrieving speedtest.net server list...")
    try:
        st.get_servers(servers=args.server)
    except NoMatchedServers:
        servers_list = ", ".join(str(s) for s in args.server)
        raise SpeedtestCLIError(f"No matched servers: {servers_list}")
    except SERVER_EXCEPTIONS as e:
        logger.error("Cannot retrieve speedtest server list")
        raise SpeedtestCLIError(e) from e
    except InvalidServerIDType:
        servers_list = ", ".join(str(s) for s in args.server)
        raise SpeedtestCLIError(
            f"{servers_list} contains an invalid server type, must be an int"
        )

    if args.server and len(args.server) == 1:
        logger.info("Retrieving information for the selected server...")
    else:
        logger.error("Selecting best server based on ping...")

    st.get_best_server()


def run_transfer_tests(st: Speedtest, args: argparse.Namespace) -> None:
    """Execute download and upload test sequences based on CLI args."""

    results = st.results

    if args.no_download:
        logger.info("Skipping download test")
    else:
        logger.info("Testing download speed")
        st.download(threads=1 if args.single else None)
        download_speed = convert_speed(results.download, args.units[1])
        logger.info(f"Download: {download_speed:.2f} M{args.units[0]}/s")

    if args.no_upload:
        logger.info("Skipping upload test")
    else:
        logger.info("Testing upload speed")
        st.upload(
            pre_allocate=not args.no_pre_allocate,
            threads=1 if args.single else None,
        )
        upload_speed = convert_speed(results.upload, args.units[1])
        logger.info(f"Upload: {upload_speed:.2f} M{args.units[0]}/s")
