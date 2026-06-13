"""
Handles CLI arguments and validation.
"""

import argparse
from http.client import HTTPSConnection

from speedtest import __version__

__all__ = ["parse_args"]


def parse_args() -> argparse.Namespace:
    """Function to handle building and parsing of command line arguments."""

    description = (
        "Command line interface for testing internet bandwidth using speedtest.net.\n"
        "--------------------------------------------------------------------------\n"
        "https://github.com/Omikorin/speedtest-cli-ng"
    )

    parser = argparse.ArgumentParser(
        prog="speedtest-cli",
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--single",
        default=False,
        action="store_true",
        help="Only use a single connection instead of multiple. Simulates a typical file transfer.",
    )
    parser.add_argument(
        "--no-download",
        dest="no_download",
        action="store_true",
        help="Do not perform download test",
    )
    parser.add_argument(
        "--no-upload",
        dest="no_upload",
        action="store_true",
        help="Do not perform upload test",
    )
    parser.add_argument(
        "--bytes",
        dest="units",
        action="store_const",
        const=("byte", 8),
        default=("bit", 1),
        help="Display values in bytes instead of bits. Does not affect image generation or JSON/CSV output.",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Generate and provide a URL to the speedtest.net share results image.",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Suppress verbose output, only show basic information",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Suppress verbose output, only show basic information in CSV format. Speeds listed in bit/s.",
    )
    parser.add_argument(
        "--csv-delimiter",
        default=",",
        type=str,
        help="Single character delimiter to use in CSV output.",
    )
    parser.add_argument("--csv-header", action="store_true", help="Print CSV headers")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Suppress verbose output, only show basic information in JSON format. Speeds listed in bit/s.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Display a list of speedtest.net servers sorted by distance",
    )
    parser.add_argument(
        "--server",
        action="append",
        type=int,
        help="Specify a server ID to test against. Can be supplied multiple times.",
    )
    parser.add_argument("--source", help="Source IP address to bind to")
    parser.add_argument(
        "--timeout", default=10, type=float, help="HTTP timeout in seconds."
    )
    parser.add_argument(
        "--secure",
        action="store_true",
        help="Use HTTPS instead of HTTP when communicating with speedtest.net operated servers",
    )
    parser.add_argument(
        "--no-pre-allocate",
        dest="no_pre_allocate",
        action="store_true",
        help="Do not pre-allocate upload data. Disable to avoid MemoryErrors on low-memory systems.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--debug", action="store_true", default=False, help="Show debugging output"
    )

    return parser.parse_args()


def validate_optional_args(args: argparse.Namespace) -> None:
    """Check if an argument was provided that depends on a missing module."""

    optional_args = {
        "secure": ("SSL support", HTTPSConnection),
    }

    for arg, info in optional_args.items():
        if getattr(args, arg, False) and info[1] is None:
            raise SystemExit(f"{info[0]} is not installed. --{arg} is unavailable")
