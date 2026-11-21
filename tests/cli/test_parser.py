"""
Tests for the CLI argument parser.
"""

import sys
from unittest.mock import patch

import pytest
from speedtest.cli.parser import parse_args


def test_parser_defaults() -> None:
    """Test that the parser sets the correct default values."""

    with patch.object(sys, "argv", ["speedtest-cli"]):
        args = parse_args()

        assert args.list is False
        assert args.server is None
        assert args.no_download is False
        assert args.no_upload is False
        assert args.threads is None
        assert args.single is False
        assert args.share is False
        assert args.units == ("b", 1)
        assert args.json is False
        assert args.debug is False
        assert args.search is None
        assert args.location is None


def test_parser_core_options() -> None:
    """Test the core server selection arguments."""

    with patch.object(sys, "argv", ["speedtest-cli", "--list", "--server", "1234"]):
        args = parse_args()

        assert args.list is True
        assert args.server == 1234

    with patch.object(sys, "argv", ["speedtest-cli", "-l", "-s", "5678"]):
        args = parse_args()

        assert args.list is True
        assert args.server == 5678


def test_parser_transfer_modifiers() -> None:
    """Test the download/upload omission flags."""

    with patch.object(sys, "argv", ["speedtest-cli", "--no-download", "--no-upload"]):
        args = parse_args()

        assert args.no_download is True
        assert args.no_upload is True


def test_parser_thread_options() -> None:
    """Test the thread configuration arguments."""

    with patch.object(sys, "argv", ["speedtest-cli", "--threads", "8"]):
        args = parse_args()
        assert args.threads == 8
        assert args.single is False

    with patch.object(sys, "argv", ["speedtest-cli", "--single"]):
        args = parse_args()
        assert args.single is True
        assert args.threads is None

    # Test mutual exclusivity of threads and single
    with patch.object(sys, "argv", ["speedtest-cli", "--threads", "4", "--single"]), pytest.raises(SystemExit):
        parse_args()


def test_parser_output_options() -> None:
    """Test display and formatting arguments."""

    with patch.object(sys, "argv", ["speedtest-cli", "--share", "--bytes", "--json", "--debug"]):
        args = parse_args()

        assert args.share is True
        assert args.units == ("B", 8)
        assert args.json is True
        assert args.debug is True


def test_parser_search_option() -> None:
    with patch.object(sys, "argv", ["speedtest-cli", "--search", "Germany"]):
        args = parse_args()

    assert args.search == "Germany"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("52.3716,4.8883", (52.3716, 4.8883)),
        ("-33.87,151.21", (-33.87, 151.21)),
        ("0,0", (0.0, 0.0)),
        ("90,-180", (90.0, -180.0)),
    ],
)
def test_parser_location_option(value: str, expected: tuple[float, float]) -> None:
    # '=' form: a bare negative number after --location would look like a flag.
    with patch.object(sys, "argv", ["speedtest-cli", f"--location={value}"]):
        args = parse_args()

    assert args.location == pytest.approx(expected)


@pytest.mark.parametrize("value", ["nonsense", "52.37", "1,2,3", "north,east", "91,0", "0,181", "-91,0"])
def test_parser_location_rejects_invalid_coordinates(value: str, capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(sys, "argv", ["speedtest-cli", f"--location={value}"]), pytest.raises(SystemExit):
        parse_args()

    assert "--location" in capsys.readouterr().err
