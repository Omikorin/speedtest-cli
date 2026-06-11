import sys
import threading
from typing import Callable, Any

DEBUG: bool = False


def print_dots(
    shutdown_event: threading.Event,
) -> Callable[[int, int, bool, bool], None]:
    """Built-in callback function used by Thread classes for printing status."""

    def inner(current: int, total: int, start: bool = False, end: bool = False) -> None:
        if shutdown_event.is_set():
            return

        if current + 1 == total and end:
            print(".", flush=True)
        else:
            print(".", end="", flush=True)

    return inner


def do_nothing(*args: Any, **kwargs: Any) -> None:
    """No-op function for suppressed callbacks."""
    pass


def printer(
    string: Any,
    quiet: bool = False,
    debug: bool = False,
    error: bool = False,
    **kwargs: Any,
) -> None:
    """Helper function to print a string with various features."""

    if debug and not DEBUG:
        return

    if error:
        kwargs["file"] = sys.stderr

    if debug:
        target_stream = kwargs.get("file", sys.stdout)

        if target_stream.isatty():
            out = f"\033[1;30mDEBUG: {string}\033[0m"
        else:
            out = f"DEBUG: {string}"
    else:
        out = str(string)

    if not quiet:
        print(out, **kwargs)
