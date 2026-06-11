import sys
import threading
from typing import Any, Callable

__all__ = ["print_dots", "do_nothing", "printer", "DEBUG"]

DEBUG: bool = False


def print_dots(
    shutdown_event: threading.Event,
) -> Callable[[int, int, bool, bool], None]:
    """
    Factory for a callback function used by network tasks to print progress dots.
    Maintains compatibility with the expected signature of (current, total, start, end).
    """

    def inner(current: int, total: int, start: bool = False, end: bool = False) -> None:
        if shutdown_event.is_set():
            return

        if current + 1 == total and end:
            print(".", flush=True)
        else:
            print(".", end="", flush=True)

    return inner


def do_nothing(*args: Any, **kwargs: Any) -> None:
    """No-op function for suppressed callbacks or quiet modes."""
    pass


def printer(
    string: Any,
    quiet: bool = False,
    debug: bool = False,
    error: bool = False,
    **kwargs: Any,
) -> None:
    """
    Helper function to print a string with various routing and formatting features.
    Handles TTY-safe ANSI coloring for debug logs and stderr routing for errors.
    """

    if quiet or (debug and not DEBUG):
        return

    # route to stderr if flagged as an error, unless the caller explicitly provided a file
    if error:
        kwargs.setdefault("file", sys.stderr)

    target_stream = kwargs.get("file", sys.stdout)
    out_string = str(string)

    if debug:
        # safely check if the stream is a real terminal to avoid polluting log files with ANSI codes
        if getattr(target_stream, "isatty", lambda: False)():
            out_string = f"\033[1;30mDEBUG: {out_string}\033[0m"
        else:
            out_string = f"DEBUG: {out_string}"

    print(out_string, **kwargs)
