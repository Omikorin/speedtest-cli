import urllib.error
import urllib.parse
import urllib.request
from hashlib import md5
from operator import attrgetter

from speedtest.engine import get_best_server, run_download_test, run_upload_test
from speedtest.exceptions import CLIError, NoMatchedServerError
from speedtest.models import RunContext, Server, SpeedtestConfig, TestResult

__all__ = ["SpeedtestClient"]


class SpeedtestClient:
    """Orchestrates high-level speedtest actions."""

    def get_target_servers(self, config: SpeedtestConfig, target_id: int | None = None, limit: int = 5) -> list[Server]:
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

    def generate_share_link(self, results: TestResult) -> str:
        """POST data to the speedtest.net API to obtain a share results link."""

        if not results.is_complete or not results.server:
            raise CLIError("Cannot generate share link: missing test results.")

        # The legacy Ookla API expects speeds in kilobits per second (kbps)
        download_kbps = round((results.download_bps or 0) / 1000.0)
        upload_kbps = round((results.upload_bps or 0) / 1000.0)
        ping = round(results.ping_ms or 0)

        hash_str = f"{ping}-{upload_kbps}-{download_kbps}-297aae72"
        hash_val = md5(hash_str.encode()).hexdigest()

        api_parameters = {
            "recommendedserverid": results.server.id,
            "ping": ping,
            "screenresolution": "",
            "promo": "",
            "download": download_kbps,
            "screendpi": "",
            "upload": upload_kbps,
            "testmethod": "http",
            "hash": hash_val,
            "touchscreen": "none",
            "startmode": "pingselect",
            "accuracy": 1,
            "bytesreceived": results.download_bytes or 0,
            "bytessent": results.upload_bytes or 0,
            "serverid": results.server.id,
        }

        api_data = urllib.parse.urlencode(api_parameters).encode()
        headers = {"Referer": "https://c.speedtest.net/flash/speedtest.swf"}

        req = urllib.request.Request(
            "https://www.speedtest.net/api/api.php", data=api_data, headers=headers, method="POST"
        )

        try:
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    raise CLIError(f"Could not submit results. HTTP {response.status}")

                body = response.read().decode(errors="ignore")

        except urllib.error.URLError as e:
            raise CLIError(f"Failed to connect to Share API: {e}") from e

        qsargs = urllib.parse.parse_qs(body)
        resultid = qsargs.get("resultid")

        if not resultid or len(resultid) != 1:
            raise CLIError("Could not parse result ID from API response.")

        return f"https://www.speedtest.net/result/{resultid[0]}.png"
