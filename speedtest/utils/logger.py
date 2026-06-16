"""
Global logging configuration for the CLI.
"""

import logging
import sys

__all__ = ["logger", "setup_logging"]

logger = logging.getLogger("speedtest")


class CLIColoredFormatter(logging.Formatter):
    """
    Custom formatter that prepends 'DEBUG: ' and applies safe ANSI colors
    only if the target stream is a genuine interactive terminal (TTY).
    """

    GREY_COLOR = "\033[1;30m"
    RESET_COLOR = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()

        if record.levelno == logging.DEBUG:
            # Safely fetch the stream attached to this formatter, fallback to stdout
            stream = getattr(self, "stream", sys.stdout)
            if hasattr(stream, "isatty") and stream.isatty():
                return f"{self.GREY_COLOR}DEBUG: {message}{self.RESET_COLOR}"
            return f"DEBUG: {message}"

        return message


class MaxLevelFilter(logging.Filter):
    """Filter to ensure logs above a specific severity do not spill into a handler."""

    def __init__(self, max_level: int) -> None:
        super().__init__()
        self.max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno <= self.max_level


def setup_logging(debug: bool = False, quiet: bool = False) -> None:
    """
    Configures the global logging pipeline infrastructure.
    Separates stdout/stderr streams and attaches custom formatting options.
    """

    logger.handlers.clear()

    if debug:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    logger.setLevel(level)

    # Route DEBUG & INFO messages cleanly to stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_formatter = CLIColoredFormatter()
    stdout_formatter.stream = sys.stdout  # Bind stream for isatty() check
    stdout_handler.setFormatter(stdout_formatter)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(MaxLevelFilter(logging.INFO))

    # Route WARNING, ERROR & CRITICAL messages cleanly to stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_formatter = CLIColoredFormatter()
    stderr_formatter.stream = sys.stderr
    stderr_handler.setFormatter(stderr_formatter)
    stderr_handler.setLevel(logging.WARNING)

    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)
