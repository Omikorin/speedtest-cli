import sys
from typing import Any

__all__ = ["printer", "DEBUG"]

DEBUG: bool = False


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
