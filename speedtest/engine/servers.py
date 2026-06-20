"""
Handles fetching, distance calculation, and latency ranking of speedtest.net servers.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.request import OpenerDirector

from speedtest.exceptions import SpeedtestBestServerFailure
from speedtest.http.request import build_request, build_user_agent, catch_request
from speedtest.models import Server
from speedtest.utils.logger import logger

__all__ = ["get_best_server"]


def _ping_server(
    server: Server,
    opener: OpenerDirector,
    headers: dict[str, Any] | None = None,
    pings: int = 3,
) -> tuple[Server, float]:
    """Ping a single server multiple times and return the average latency."""

    headers = headers or {}
    url: str = server.url.replace("upload.php", "latency.txt")

    if not url:
        return server, 3600.0

    latencies = []

    for i in range(pings):
        request = build_request(url, headers=headers, bump=str(i))
        start = time.monotonic()

        uh, e = catch_request(request, opener=opener)

        if e or not uh:
            latencies.append(3600.0)
            continue

        with uh:
            if int(getattr(uh, "code", 500)) != 200:
                latencies.append(3600.0)
                continue

            latency = time.monotonic() - start
            latencies.append(latency)

    # in milliseconds
    avg_latency = sum(latencies) / len(latencies) * 1000.0

    return server, avg_latency


def get_best_server(closest_servers: list[Server], opener: OpenerDirector) -> tuple[Server, float]:
    """
    Concurrently ping the closest servers to determine which has the lowest latency.
    """

    best_server = None
    lowest_latency = float("inf")

    user_agent = build_user_agent()
    headers = {"User-Agent": user_agent}

    with ThreadPoolExecutor(max_workers=len(closest_servers)) as executor:
        future_to_server = {
            executor.submit(_ping_server, server, opener, headers): server
            for server in closest_servers
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
