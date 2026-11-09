"""
Tests for the main entry point.
"""

from unittest.mock import MagicMock, patch

import pytest
from speedtest.__main__ import main
from speedtest.engine.config import ConfigFetchError
from speedtest.exceptions import CLIError, SpeedtestError
from speedtest.utils import ExitStatus


class MockSpeedtestError(SpeedtestError):
    """Subclass of SpeedtestError declaring a code attribute to satisfy strict typing."""

    code: int


@patch("speedtest.__main__.shell")
def test_main_success(mock_shell: MagicMock) -> None:
    """Test that a successful shell execution returns its exit status."""

    mock_shell.return_value = ExitStatus.SUCCESS.value

    status = main()

    assert status == ExitStatus.SUCCESS.value
    mock_shell.assert_called_once()


@patch("speedtest.__main__.logger")
@patch("speedtest.__main__.shell")
def test_main_keyboard_interrupt(mock_shell: MagicMock, mock_logger: MagicMock) -> None:
    """Test that Ctrl+C is caught, logged, and returns the correct error code."""

    mock_shell.side_effect = KeyboardInterrupt()

    status = main()

    assert status == ExitStatus.ERROR_CTRL_C.value
    mock_logger.error.assert_called_once_with("Stopped by user")


@patch("speedtest.__main__.logger")
@patch("speedtest.__main__.shell")
def test_main_speedtest_error_default_code(mock_shell: MagicMock, mock_logger: MagicMock) -> None:
    """Test that a generic SpeedtestError falls back to the default ERROR exit status."""

    mock_shell.side_effect = SpeedtestError("A standard speedtest error occurred.")

    status = main()

    assert status == ExitStatus.ERROR.value
    mock_logger.error.assert_called_once_with("A standard speedtest error occurred.")


@patch("speedtest.__main__.logger")
@patch("speedtest.__main__.shell")
def test_main_speedtest_error_with_custom_code(mock_shell: MagicMock, mock_logger: MagicMock) -> None:
    """Test that a SpeedtestError with a specific code returns that exact code."""

    error = MockSpeedtestError("A specific domain error.")
    error.code = 99
    mock_shell.side_effect = error

    status = main()

    assert status == 99
    mock_logger.error.assert_called_once_with("A specific domain error.")


@pytest.mark.parametrize("error", [ValueError("bad"), RuntimeError("bad"), OSError("bad")])
@patch("speedtest.__main__.logger")
@patch("speedtest.__main__.shell")
def test_main_unexpected_exception(mock_shell: MagicMock, mock_logger: MagicMock, error: Exception) -> None:
    """Test that unhandled exceptions are caught and logged securely."""

    mock_shell.side_effect = error

    status = main()

    assert status == ExitStatus.ERROR.value
    mock_logger.exception.assert_called_once_with("An unexpected error occurred.")


@pytest.mark.parametrize("code", [ExitStatus.SUCCESS.value, ExitStatus.ERROR_CTRL_C.value])
@patch("speedtest.__main__.logger")
@patch("speedtest.__main__.shell")
def test_main_error_with_quiet_exit_code_is_not_logged(
    mock_shell: MagicMock, mock_logger: MagicMock, code: int
) -> None:
    """Errors that map to success or Ctrl+C codes must not print a message."""

    error = MockSpeedtestError("already handled")
    error.code = code
    mock_shell.side_effect = error

    assert main() == code
    mock_logger.error.assert_not_called()


@patch("speedtest.__main__.logger")
@patch("speedtest.__main__.shell")
def test_main_empty_error_message_falls_back_to_repr(mock_shell: MagicMock, mock_logger: MagicMock) -> None:
    mock_shell.side_effect = SpeedtestError()

    main()

    mock_logger.error.assert_called_once_with("SpeedtestError()")


@patch("speedtest.cli.runner.parse_args")
@patch("speedtest.cli.runner.get_config")
def test_main_reports_config_failure_instead_of_crashing(
    mock_get_config: MagicMock, mock_parse: MagicMock, caplog: pytest.LogCaptureFixture
) -> None:
    """End to end through the real shell: a blocked config fetch is an error exit code, not a traceback."""

    mock_parse.return_value = MagicMock(
        list=False, debug=False, json=False, server=None, no_download=False, no_upload=False,
        single=False, threads=None, share=False, units=("b", 1),
    )  # fmt: skip
    mock_get_config.side_effect = ConfigFetchError("HTTP 403: Failed to fetch config.")

    status = main()

    assert status == ExitStatus.ERROR.value
    assert "HTTP 403: Failed to fetch config." in caplog.text


def test_cli_error_is_a_speedtest_error() -> None:
    assert issubclass(CLIError, SpeedtestError)
