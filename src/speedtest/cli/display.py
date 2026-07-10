"""
Handles terminal output and presentation logic for the CLI.
"""

import dataclasses
import json
import sys
from datetime import UTC, datetime

from rich.table import Table

from speedtest.models import Server, SpeedtestConfig, TestResult
from speedtest.utils.logger import console
from speedtest.utils.status import ExitStatus

__all__ = ["print_json", "print_server_list"]


def print_server_list(servers: list[Server]) -> int:
    """Print nearby servers in a table."""

    table = Table(title="Available Target Servers")

    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Distance", justify="right", style="green", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Country", style="blue")
    table.add_column("Sponsor", style="yellow")

    for server in servers:
        table.add_row(
            str(server.id),
            f"{server.distance} km",
            server.name,
            server.country,
            server.sponsor,
        )

    try:
        console.print(table)
    except BrokenPipeError:
        pass

    return ExitStatus.SUCCESS.value


def print_json(results: TestResult, client_config: SpeedtestConfig | None = None) -> None:
    """Print the machine-readable JSON representation."""

    json_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "ping": results.ping_ms,
        "download": results.download_bps,
        "upload": results.upload_bps,
        "bytes_received": results.download_bytes,
        "bytes_sent": results.upload_bytes,
        "share": results.share_url,
        "server": dataclasses.asdict(results.server) if results.server else None,
    }

    if client_config:
        json_data["client"] = {
            "ip": client_config.ip_address,
            "isp": client_config.isp_name,
            "isp_id": client_config.isp_id,
            "location": dataclasses.asdict(client_config.location),
        }

    indent = 2 if sys.stdout.isatty() else None
    print(json.dumps(json_data, indent=indent))
