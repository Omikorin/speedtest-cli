"""
Global logging configuration for the CLI.
"""

import logging

from rich.console import Console
from rich.logging import RichHandler

__all__ = ["console", "logger", "setup_logging"]

logger = logging.getLogger("speedtest")
console = Console()
error_console = Console(stderr=True)


def setup_logging(debug: bool = False, quiet: bool = False) -> None:
    """Configures global logging pipeline using rich."""

    logger.handlers.clear()

    console.quiet = quiet

    if debug:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    else:
        level = logging.INFO

    logger.setLevel(level)

    # Quiet mode reserves stdout for JSON, so log records move to stderr instead of vanishing.
    handler = RichHandler(
        console=error_console if quiet else console,
        show_time=debug,
        show_level=True,
        show_path=debug,
        rich_tracebacks=True,
        markup=True,
    )

    logger.addHandler(handler)
