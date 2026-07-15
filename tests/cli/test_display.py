"""
Tests for CLI output and presentation logic.
"""

import json
import sys
from unittest.mock import patch

import pytest
from pytest import CaptureFixture
from speedtest.cli.display import print_json, print_server_list
from speedtest.models import ApiConfig, Server
from speedtest.models import TestResult as SpeedtestResult
from speedtest.utils import ExitStatus


def test_print_server_list_success(mock_server: Server) -> None:
    """Test that printing the server table works correctly and returns SUCCESS."""

    with patch("speedtest.cli.display.console.print") as mock_print:
        status = print_server_list([mock_server])

        assert status == ExitStatus.SUCCESS.value
        mock_print.assert_called_once()

        table_arg = mock_print.call_args[0][0]
        assert table_arg.title == "Available Target Servers"
        assert len(table_arg.columns) == 5


def test_print_server_list_broken_pipe(mock_server: Server) -> None:
    """Test that a BrokenPipeError (like piping to `head` or `less`) is handled cleanly."""

    with patch("speedtest.cli.display.console.print", side_effect=BrokenPipeError) as mock_print:
        status = print_server_list([mock_server])

        # It should catch the error and quit successfully
        assert status == ExitStatus.SUCCESS.value
        mock_print.assert_called_once()


def test_print_json_without_client_config(capsys: CaptureFixture[str], mock_result: SpeedtestResult) -> None:
    """Test JSON printing when no client config is provided (compact mode)."""

    # Mock sys.stdout.isatty to False for compact JSON (indent=None)
    with patch.object(sys.stdout, "isatty", return_value=False):
        print_json(mock_result, client_config=None)

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert "timestamp" in data
    assert data["ping"] == pytest.approx(15.5)
    assert data["download"] == pytest.approx(100_000_000.0)
    assert data["share"] == "http://speedtest.example.com/result/123"
    assert data["server"]["id"] == 1234

    assert "client" not in data


def test_print_json_with_client_config(
    capsys: CaptureFixture[str], mock_result: SpeedtestResult, mock_api_config: ApiConfig
) -> None:
    """Test JSON output includes the client configuration when provided."""

    # Mock sys.stdout.isatty to False for compact JSON (indent=None)
    with patch.object(sys.stdout, "isatty", return_value=False):
        print_json(mock_result, client_config=mock_api_config)

    captured = capsys.readouterr()
    data = json.loads(captured.out)

    assert "client" in data
    assert data["client"]["ip"] == "1.1.1.1"
    assert data["client"]["isp"] == "Acme Internet"
    assert data["client"]["isp_id"] == 54321

    # dataclasses.asdict() should have unpacked the location
    assert data["client"]["location"]["latitude"] == pytest.approx(40.0)
    assert data["client"]["location"]["longitude"] == pytest.approx(-74.0)


def test_print_json_tty_indenting(capsys: CaptureFixture[str]) -> None:
    """Test JSON output formats with indent=2 when attached to a TTY."""

    result = SpeedtestResult(ping_ms=10.0)

    # Mock sys.stdout.isatty to True to trigger indent=2
    with patch.object(sys.stdout, "isatty", return_value=True):
        print_json(result, client_config=None)

    captured = capsys.readouterr()

    assert '{\n  "timestamp":' in captured.out
