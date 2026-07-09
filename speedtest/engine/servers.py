"""
Handles latency ranking of speedtest.net servers using raw TCP handshakes.
"""

import socket
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

from speedtest.engine.network import measure_tcp_latency
from speedtest.exceptions import SpeedtestBestServerFailure
from speedtest.models import Server
from speedtest.utils.logger import logger

__all__ = ["find_fastest_server", "get_best_server"]


def _ping_server(server: Server, pings: int = 10) -> tuple[Server, float]:
    """Ping a single server using raw TCP handshakes and return the average latency."""

    if not server.url:
        return server, 3600000.0  # 1 hour penalty in ms

    parsed = urlparse(server.url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    if not host:
        return server, 3600000.0

    try:
        ip = socket.gethostbyname(host)
    except socket.gaierror:
        logger.debug(f"DNS resolution failed for {host}")
        return server, 3600000.0

    latencies = [measure_tcp_latency(ip, port) for _ in range(pings)]

    avg_latency = sum(latencies) / len(latencies) if latencies else 3600000.0
    return server, avg_latency


def find_fastest_server(results: Iterable[tuple[Server, float]]) -> tuple[Server, float]:
    """Pure function to evaluate and return the fastest server from a sequence of results."""

    try:
        return min(results, key=lambda x: x[1])
    except ValueError:
        raise SpeedtestBestServerFailure("Unable to determine best server via latency pings.")


def get_best_server(closest_servers: list[Server]) -> tuple[Server, float]:
    """Concurrently ping the closest servers to determine the lowest latency."""

    if not closest_servers:
        raise SpeedtestBestServerFailure("No servers provided to ping.")

    def _execute_pings() -> Iterable[tuple[Server, float]]:
        """Generator orchestrating concurrent TCP pings."""

        with ThreadPoolExecutor(max_workers=len(closest_servers)) as executor:
            future_to_server = {
                executor.submit(_ping_server, server): server for server in closest_servers
            }

            for future in as_completed(future_to_server):
                try:
                    yield future.result()
                except Exception as e:
                    logger.debug(f"Server TCP ping generated an exception: {e}")

    best_server, lowest_latency = find_fastest_server(_execute_pings())

    return best_server, lowest_latency
