"""
Tests for the global logging configuration.
"""

import logging
from unittest.mock import MagicMock, patch

from speedtest.utils.logger import console, logger, setup_logging


@patch("speedtest.utils.logger.RichHandler")
def test_setup_logging_default(mock_rich_handler: MagicMock) -> None:
    """Test the standard logging configuration."""

    setup_logging()

    assert console.quiet is False
    assert logger.level == logging.INFO

    mock_rich_handler.assert_called_once_with(
        console=console,
        show_time=False,
        show_level=True,
        show_path=False,
        rich_tracebacks=True,
        markup=True,
    )


@patch("speedtest.utils.logger.RichHandler")
def test_setup_logging_debug(mock_rich_handler: MagicMock) -> None:
    """Test that debug mode lowers the log level and adds rich trace details."""

    setup_logging(debug=True)

    assert console.quiet is False
    assert logger.level == logging.DEBUG

    # Debug mode should explicitly enable time and path rendering
    mock_rich_handler.assert_called_once_with(
        console=console,
        show_time=True,
        show_level=True,
        show_path=True,
        rich_tracebacks=True,
        markup=True,
    )


@patch("speedtest.utils.logger.RichHandler")
def test_setup_logging_quiet(mock_rich_handler: MagicMock) -> None:
    """Test that quiet mode silences the console and raises the log level to WARNING."""

    setup_logging(quiet=True)

    assert console.quiet is True
    assert logger.level == logging.WARNING

    mock_rich_handler.assert_called_once_with(
        console=console,
        show_time=False,
        show_level=True,
        show_path=False,
        rich_tracebacks=True,
        markup=True,
    )


@patch("speedtest.utils.logger.RichHandler")
def test_setup_logging_debug_and_quiet(mock_rich_handler: MagicMock) -> None:
    """Test the priority when both debug and quiet modes are requested."""

    setup_logging(debug=True, quiet=True)

    # The console should be muted due to quiet=True
    assert console.quiet is True

    # However, because debug check comes first in the if/elif chain, the log level should be DEBUG
    assert logger.level == logging.DEBUG

    mock_rich_handler.assert_called_once_with(
        console=console,
        show_time=True,
        show_level=True,
        show_path=True,
        rich_tracebacks=True,
        markup=True,
    )
