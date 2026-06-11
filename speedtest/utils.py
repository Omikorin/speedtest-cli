import math
import sys
import threading
from typing import Callable, Any

DEBUG: bool = False


def distance(origin: tuple[float, float], destination: tuple[float, float]) -> float:
    """Determine distance between 2 sets of [lat, lon] in km using the Haversine formula."""

    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371.0  # km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (math.sin(dlat / 2) ** 2) + (
        math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * (math.sin(dlon / 2) ** 2)
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return radius * c


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
