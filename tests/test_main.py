"""
Tests for the main entry point.
"""

from unittest.mock import MagicMock, patch

from speedtest.__main__ import main
from speedtest.exceptions import SpeedtestError
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


@patch("speedtest.__main__.logger")
@patch("speedtest.__main__.shell")
def test_main_unexpected_exception(mock_shell: MagicMock, mock_logger: MagicMock) -> None:
    """Test that unhandled exceptions are caught and logged securely."""

    mock_shell.side_effect = ValueError("Something completely unexpected crashed.")

    status = main()

    assert status == ExitStatus.ERROR.value
    mock_logger.exception.assert_called_once_with("An unexpected error occurred.")
