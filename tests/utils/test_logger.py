"""
Tests for the global logging configuration.
"""

import logging
from io import StringIO

import pytest
from speedtest.utils import console, logger, setup_logging


@pytest.fixture
def output(monkeypatch: pytest.MonkeyPatch) -> StringIO:
    """Capture what the console would actually print."""

    buffer = StringIO()
    monkeypatch.setattr(console, "file", buffer)
    return buffer


def test_setup_logging_default_shows_info_and_errors(output: StringIO) -> None:
    setup_logging()

    logger.debug("debug-line")
    logger.info("info-line")
    logger.error("error-line")

    text = output.getvalue()
    assert "debug-line" not in text
    assert "info-line" in text
    assert "error-line" in text
    assert logger.level == logging.INFO


def test_setup_logging_debug_shows_debug_lines(output: StringIO) -> None:
    setup_logging(debug=True)

    logger.debug("debug-line")

    assert "debug-line" in output.getvalue()
    assert logger.level == logging.DEBUG


def test_setup_logging_quiet_hides_info(output: StringIO) -> None:
    setup_logging(quiet=True)

    logger.info("info-line")

    assert output.getvalue() == ""
    assert logger.level == logging.WARNING


def test_quiet_mode_still_reports_errors(output: StringIO, capsys: pytest.CaptureFixture[str]) -> None:
    """With --json, stdout is reserved for JSON, but failures must still reach the user on stderr."""

    setup_logging(quiet=True)

    logger.error("error-line")

    assert output.getvalue() == ""  # nothing may leak into stdout
    assert "error-line" in capsys.readouterr().err


def test_setup_logging_debug_and_quiet_keeps_stdout_clean(output: StringIO) -> None:
    """--debug --json: debug lines are produced, but stdout stays clean for the JSON document."""

    setup_logging(debug=True, quiet=True)

    logger.debug("debug-line")

    assert logger.level == logging.DEBUG
    assert output.getvalue() == ""


def test_setup_logging_is_idempotent() -> None:
    setup_logging()
    setup_logging(debug=True)

    assert len(logger.handlers) == 1
