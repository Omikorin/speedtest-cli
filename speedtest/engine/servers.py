"""
Handles fetching, distance calculation, and latency ranking of speedtest.net servers.
"""

import math
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.request import OpenerDirector

from speedtest.exceptions import ServersRetrievalError, SpeedtestBestServerFailure
from speedtest.http.request import build_request, build_user_agent, catch_request
from speedtest.http.response import get_response_stream
from speedtest.utils.logger import logger

__all__ = ["fetch_servers", "get_best_server"]


def _calculate_distance(
    origin: tuple[float, float], destination: tuple[float, float]
) -> float:
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


def fetch_servers(
    opener: OpenerDirector,
    lat_lon: tuple[float, float],
    ignore_servers: list[int] | None = None,
) -> dict[float, list[dict[str, Any]]]:
    """
    Fetch the server list from speedtest.net, parse the XML, calculate
    distances from the client, and return a dictionary grouped and sorted by distance.
    """

    ignore_servers = ignore_servers or []
    urls = [
        "https://c.speedtest.net/speedtest-servers-static.php",
        "https://www.speedtest.net/speedtest-servers-static.php",
    ]

    servers_dict: defaultdict[float, list[dict[str, Any]]] = defaultdict(list)

    for url in urls:
        request = build_request(url)
        uh, e = catch_request(request, opener=opener)

        if e or not uh:
            continue

        with uh:
            if int(getattr(uh, "code", 500)) != 200:
                continue

            try:
                with get_response_stream(uh) as stream:
                    serversxml = stream.read()
            except (OSError, EOFError):
                continue

        logger.debug(f"Servers XML:\n{serversxml.decode(errors='ignore')}")

        try:
            root = ET.fromstring(serversxml)
        except ET.ParseError:
            continue

        for server in root.findall(".//server"):
            attrib = server.attrib
            server_id = int(attrib.get("id", 0))

            if not server_id or server_id in ignore_servers:
                continue

            try:
                lat_str, lon_str = attrib.get("lat"), attrib.get("lon")
                if not lat_str or not lon_str:
                    continue

                server_lat_lon = (float(lat_str), float(lon_str))
                distance = _calculate_distance(lat_lon, server_lat_lon)
            except (ValueError, TypeError):
                continue

            attrib["d"] = distance # type: ignore
            servers_dict[distance].append(attrib)

        if servers_dict:
            break

    if not servers_dict:
        raise ServersRetrievalError(
            "Failed to retrieve or parse speedtest server list."
        )

    logger.debug(f"Discovered {sum(len(s) for s in servers_dict.values())} servers.")

    return dict(servers_dict)


def _ping_server(
    server: dict[str, Any],
    opener: OpenerDirector,
    headers: dict[str, Any] | None = None,
    pings: int = 3,
) -> tuple[dict[str, Any], float]:
    """Ping a single server multiple times and return the average latency."""

    headers = headers or {}
    url: str = server.get("url", "").replace("upload.php", "latency.txt")

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

    avg_latency = sum(latencies) / len(latencies)
    server["latency"] = avg_latency
    server["latency_ms"] = avg_latency * 1000.0

    return server, avg_latency


def get_best_server(
    closest_servers: list[dict[str, Any]], opener: OpenerDirector
) -> dict[str, Any]:
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
        raise SpeedtestBestServerFailure(
            "Unable to determine best server via latency pings."
        )

    logger.debug(
        f"Best server selected: {best_server.get('sponsor')} "
        f"({best_server.get('name')}) with latency {best_server.get('latency_ms', 0.0):.4f} ms"
    )

    return best_server
