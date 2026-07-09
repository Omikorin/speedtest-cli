"""
Handles formatting of test results into strings.
"""

import dataclasses
import json
import sys
from datetime import UTC, datetime

from speedtest.models import SpeedtestConfig, TestResult

__all__ = ["format_json", "format_text"]


def format_json(results: TestResult, client_config: SpeedtestConfig | None = None) -> str:
    """Construct the machine-readable JSON representation as a string."""

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
    return json.dumps(json_data, indent=indent)


def format_text(results: TestResult, units: tuple[str, int]) -> str:
    """Format the human-readable text representation as a string."""

    unit_name, unit_divisor = units
    lines: list[str] = []

    dl_speed = results.get_download_speed(unit_divisor)
    dl_bytes = results.get_downloaded_megabytes()

    if dl_speed is not None and dl_bytes is not None:
        lines.append(f"Download: {dl_speed:.2f} M{unit_name}/s ({dl_bytes:.2f} MB)")

    ul_speed = results.get_upload_speed(unit_divisor)
    ul_bytes = results.get_uploaded_megabytes()

    if ul_speed is not None and ul_bytes is not None:
        lines.append(f"Upload: {ul_speed:.2f} M{unit_name}/s ({ul_bytes:.2f} MB)")

    if results.share_url is not None:
        lines.append(f"Share results: {results.share_url}")

    return "\n".join(lines)
