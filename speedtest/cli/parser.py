"""
Handles CLI arguments and validation.
"""

import argparse

from speedtest import __version__

__all__ = ["parse_args"]


def parse_args() -> argparse.Namespace:
    """Function to handle building and parsing of command line arguments."""

    description = (
        "Next generation CLI for testing internet bandwidth using speedtest.net.\n"
        "--------------------------------------------------------------------------\n"
        "https://github.com/Omikorin/speedtest-cli"
    )

    parser = argparse.ArgumentParser(
        prog="speedtest-cli",
        description=description,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    core_group = parser.add_argument_group("Core Options")
    core_group.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="Show available speedtest.net servers sorted by distance.",
    )
    core_group.add_argument(
        "-s",
        "--server",
        type=int,
        help="Specify a server id to test against.",
    )

    transfer_group = parser.add_argument_group("Transfer Modifiers")
    transfer_group.add_argument(
        "--no-download",
        action="store_true",
        help="Do not perform the download test.",
    )
    transfer_group.add_argument(
        "--no-upload",
        action="store_true",
        help="Do not perform the upload test.",
    )

    threads_group = transfer_group.add_mutually_exclusive_group()
    threads_group.add_argument(
        "-t",
        "--threads",
        type=int,
        help="Set the number of concurrent connections instead of using downloaded config.",
    )
    threads_group.add_argument(
        "--single",
        action="store_true",
        help="Use one concurrent connection. Simulates a typical file transfer.",
    )

    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument(
        "--share",
        action="store_true",
        help="Generate and provide a URL to the speedtest.net share results image.",
    )
    output_group.add_argument(
        "--bytes",
        dest="units",
        action="store_const",
        const=("byte", 8),
        default=("bit", 1),
        help=(
            "Display values in bytes instead of bits. "
            "Does not affect image generation or JSON output."
        ),
    )

    format_group = output_group.add_mutually_exclusive_group()
    format_group.add_argument(
        "--json",
        action="store_true",
        help=(
            "Suppress verbose output, only show basic information "
            "in JSON format. Speeds listed in bit/s."
        ),
    )

    # conn_group = parser.add_argument_group("Connection Options")
    # conn_group.add_argument(
    #     "--source", type=str, help="Bind a source IP address to use for connections."
    # )
    # conn_group.add_argument("--timeout", default=10.0, type=float, help="HTTP timeout in seconds")

    misc_group = parser.add_argument_group("Miscellaneous Options")
    misc_group.add_argument("--debug", action="store_true", help="Show verbose debugging output.")
    misc_group.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    return parser.parse_args()
