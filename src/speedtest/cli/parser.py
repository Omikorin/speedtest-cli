"""
Handles CLI arguments and validation.
"""

import argparse

from speedtest import __version__

__all__ = ["parse_args"]


def _coordinates(value: str) -> tuple[float, float]:
    """Parse `LAT,LON` into a validated coordinate pair."""

    try:
        latitude_text, longitude_text = value.split(",")
        latitude, longitude = float(latitude_text), float(longitude_text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid coordinates {value!r}, expected LAT,LON like 52.37,4.89") from None

    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise argparse.ArgumentTypeError(f"coordinates out of range: {value!r}")

    return latitude, longitude


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
    core_group.add_argument(
        "--search",
        help="Find servers matching a country or city name, anywhere in the world.",
    )
    core_group.add_argument(
        "--location",
        type=_coordinates,
        metavar="LAT,LON",
        help="Find servers near these coordinates instead of near your IP address.",
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
        const=("B", 8),
        default=("b", 1),
        help=("Display values in bytes instead of bits. Does not affect image generation or JSON output."),
    )

    format_group = output_group.add_mutually_exclusive_group()
    format_group.add_argument(
        "--json",
        action="store_true",
        help=("Suppress verbose output, only show basic information in JSON format. Speeds listed in bit/s."),
    )

    misc_group = parser.add_argument_group("Miscellaneous Options")
    misc_group.add_argument("--debug", action="store_true", help="Show verbose debugging output.")
    misc_group.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    return parser.parse_args()
