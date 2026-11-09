import json
from hashlib import md5
from operator import attrgetter

import httpx2

from speedtest.engine import get_best_server, run_download_test, run_upload_test
from speedtest.engine.network import build_user_agent
from speedtest.exceptions import CLIError, NoMatchedServerError
from speedtest.models import ApiConfig, RunContext, Server, SpeedtestResult

__all__ = ["SpeedtestClient"]


class SpeedtestClient:
    """Orchestrates high-level speedtest actions."""

    def get_target_servers(self, config: ApiConfig, target_id: int | None = None, limit: int = 5) -> list[Server]:
        """Sorts available servers by distance and filters by ID if requested."""

        servers = sorted(config.servers, key=attrgetter("distance"))

        if target_id is not None:
            servers = [srv for srv in servers if srv.id == target_id]
            if not servers:
                raise NoMatchedServerError(f"No server matched the ID: {target_id}")

        return servers[:limit]

    def select_best_server(self, servers: list[Server]) -> tuple[Server, float]:
        """Pings a list of servers and returns the fastest one alongside its latency."""

        if not servers:
            raise CLIError("No servers provided to test against.")

        best_server, latency = get_best_server(servers)

        if not best_server:
            raise CLIError("Failed to identify a valid best server.")

        return best_server, latency

    def download(self, server: Server, ctx: RunContext) -> tuple[int, float]:
        """Executes the download test. Returns (bytes_received, download_speed)."""

        if not server.url:
            raise CLIError("The target server is missing a valid URL.")

        return run_download_test(best_server_url=server.url, ctx=ctx)

    def upload(self, server: Server, ctx: RunContext) -> tuple[int, float]:
        """Executes the upload test. Returns (bytes_sent, upload_speed)."""

        if not server.url:
            raise CLIError("The target server is missing a valid URL.")

        return run_upload_test(best_server_url=server.url, ctx=ctx)

    def generate_share_link(self, results: SpeedtestResult, config: ApiConfig) -> str:
        """POST data to the speedtest.net API to obtain a share results link."""

        if results.ping_ms is None or not results.server:
            raise CLIError("Cannot generate share link: missing test results.")

        # The web client reports kbps and signs ping-upload-download with a fixed salt.
        download_kbps = round((results.download_bps or 0) / 1000.0)
        upload_kbps = round((results.upload_bps or 0) / 1000.0)
        ping = round(results.ping_ms)

        hash_val = md5(f"{ping}-{upload_kbps}-{download_kbps}-817d699764d33f89c".encode()).hexdigest()
        host, _, port = results.server.host.partition(":")

        payload: dict[str, object] = {
            "app": {"sdk": {"commit": "a36027299986af441deb58cd730f432fcad58871", "version": "3.1.1"}},
            "serverid": results.server.id,
            "testmethod": "http,http,http",
            "source": "st4-js",
            "configs": {"host": host, "port": int(port) if port else 8080},
            "ping": ping,
            "ispName": config.isp_name,
            "guid": config.guid,
            "hash": hash_val,
            "clientip": config.ip_address,
        }
        if download_kbps:
            payload["download"] = download_kbps
        if upload_kbps:
            payload["upload"] = upload_kbps

        headers = {
            "User-Agent": build_user_agent(),
            "Accept": "application/json",
            "Origin": "https://www.speedtest.net",
            "Referer": "https://www.speedtest.net/",
            "Content-Type": "application/json;charset=UTF-8",
        }

        body = ""
        try:
            response = httpx2.post(
                "https://www.speedtest.net/api/results.php",
                content=json.dumps(payload),
                headers=headers,
                timeout=10.0,
            )
            response.raise_for_status()
            body = response.text
            resultid = response.json().get("resultid")

        except httpx2.HTTPStatusError as e:
            raise CLIError(f"Could not submit results. HTTP {e.response.status_code}") from e
        except httpx2.RequestError as e:
            raise CLIError(f"Failed to connect to Share API: {e}") from e
        except ValueError, AttributeError:
            resultid = None

        if not resultid:
            raise CLIError(f"Could not parse result ID from API response: {body[:200]!r}")

        return f"https://www.speedtest.net/result/{resultid}.png"
