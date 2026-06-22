"""
Wraps the core Speedtest logic into CLI actions.
"""

from speedtest.models import Server
from speedtest.utils.status import ExitStatus

__all__ = ["handle_server_list"]


def handle_server_list(servers: list[Server]) -> int:
    """Handle the --list argument by printing nearby servers and exiting."""

    try:
        for server in servers:
            line = (
                f"[{server.id:>5}]\t{server.distance} km\t"
                f"{server.name} ({server.country}) "
                f"by {server.sponsor}"
            )
            print(line)
    except BrokenPipeError:
        # Prevents messy tracebacks if the user pipes output to `head` or `less`
        pass

    return ExitStatus.SUCCESS.value
