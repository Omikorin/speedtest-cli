import logging
import sys

__all__ = ["setup_logging", "logger"]

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
            if sys.stdout.isatty():
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


def setup_logging(debug: bool = False) -> None:
    """
    Configures the global logging pipeline infrastructure.
    Separates stdout/stderr streams and attaches custom formatting options.
    """

    logger.handlers.clear()

    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Route DEBUG & INFO messages cleanly to stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(MaxLevelFilter(logging.INFO))
    stdout_handler.setFormatter(CLIColoredFormatter())

    # Route WARNING, ERROR & CRITICAL messages cleanly to stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(CLIColoredFormatter())

    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)
