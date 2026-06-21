"""
Handles latency ranking of speedtest.net servers.
"""

import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from speedtest.engine.network import build_user_agent
from speedtest.exceptions import SpeedtestBestServerFailure
from speedtest.models import Server
from speedtest.utils.logger import logger

__all__ = ["get_best_server"]


def _ping_server(
    server: Server,
    headers: dict[str, str] | None = None,
    pings: int = 3,
) -> tuple[Server, float]:
    """Ping a single server multiple times and return the average latency in milliseconds."""

    if not server.url:
        return server, 3600000.0  # 1 hour penalty in ms

    base_url = server.url.replace("upload.php", "latency.txt")
    latencies: list[float] = []
    req_headers = headers or {}

    for i in range(pings):
        cache_buster = int(time.time() * 1000)
        target_url = f"{base_url}?x={cache_buster}.{i}"

        req = urllib.request.Request(target_url, headers=req_headers)
        start_time = time.monotonic()

        try:
            with urllib.request.urlopen(req, timeout=5.0) as response:
                if response.status == 200:
                    response.read()
                    latencies.append(time.monotonic() - start_time)
                else:
                    latencies.append(3600.0)

        except urllib.error.URLError:
            latencies.append(3600.0)

    avg_latency_s = sum(latencies) / len(latencies) if latencies else 3600.0

    return server, avg_latency_s * 1000.0


def get_best_server(closest_servers: list[Server]) -> tuple[Server, float]:
    """
    Concurrently ping the closest servers to determine which has the lowest latency.
    """

    if not closest_servers:
        raise SpeedtestBestServerFailure("No servers provided to ping.")

    best_server = None
    lowest_latency = float("inf")

    headers = {"User-Agent": build_user_agent()}

    with ThreadPoolExecutor(max_workers=len(closest_servers)) as executor:
        future_to_server = {
            executor.submit(_ping_server, server, headers): server for server in closest_servers
        }

        for future in as_completed(future_to_server):
            try:
                server, latency = future.result()
                if latency < lowest_latency:
                    lowest_latency = latency
                    best_server = server
            except Exception as e:
                logger.debug(f"Server ping generated an exception: {e}")

    if best_server is None:
        raise SpeedtestBestServerFailure("Unable to determine best server via latency pings.")

    logger.debug(
        f"Best server selected: {best_server.sponsor} "
        f"({best_server.name}) with latency {lowest_latency:.4f} ms"
    )

    return best_server, lowest_latency
