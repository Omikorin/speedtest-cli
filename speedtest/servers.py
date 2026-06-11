import math
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Tuple

from speedtest.exceptions import ServersRetrievalError, SpeedtestBestServerFailure
from speedtest.http import (
    build_request,
    build_user_agent,
    catch_request,
    get_response_stream,
)
from speedtest.utils import printer

__all__ = ["fetch_servers", "get_best_server"]


def _calculate_distance(
    origin: Tuple[float, float], destination: Tuple[float, float]
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
    opener: Any,
    lat_lon: Tuple[float, float],
    ignore_servers: List[int] = None,
    secure: bool = False,
) -> Dict[float, List[Dict[str, Any]]]:
    """
    Fetch the server list from speedtest.net, parse the XML, calculate
    distances from the client, and return a dictionary grouped and sorted by distance.
    """

    ignore_servers = ignore_servers or []
    urls = [
        "://c.speedtest.net/speedtest-servers-static.php",
        "://www.speedtest.net/speedtest-servers-static.php",
    ]

    servers: Dict[float, List[Dict[str, Any]]] = {}

    for url in urls:
        request = build_request(url, secure=secure)
        uh, e = catch_request(request, opener=opener)
        if e:
            continue

        stream = get_response_stream(uh)
        serversxml = stream.read()
        stream.close()
        uh.close()

        if int(uh.code) != 200:
            continue

        printer(f"Servers XML:\n{serversxml.decode(errors='ignore')}", debug=True)

        try:
            root = ET.fromstring(serversxml)
        except ET.ParseError:
            continue

        for server in root.findall(".//server"):
            attrib = server.attrib
            server_id = int(attrib.get("id", 0))

            if server_id in ignore_servers:
                continue

            try:
                server_lat_lon = (float(attrib.get("lat")), float(attrib.get("lon")))
                distance = _calculate_distance(lat_lon, server_lat_lon)
            except (ValueError, TypeError):
                continue

            attrib["d"] = distance

            if distance not in servers:
                servers[distance] = []
            servers[distance].append(attrib)

        # if we successfully parsed servers from this URL, stop trying fallbacks
        if servers:
            break

    if not servers:
        raise ServersRetrievalError(
            "Failed to retrieve or parse speedtest server list."
        )

    printer(f"Discovered {sum(len(s) for s in servers.values())} servers.", debug=True)
    return servers


def _ping_server(
    server: Dict[str, Any], opener: Any, headers: Dict[str, Any] = {}, pings: int = 3
) -> Tuple[Dict[str, Any], float]:
    """Ping a single server multiple times and return the average latency."""

    url = server.get("url", "").replace("upload.php", "latency.txt")
    latencies = []

    for i in range(pings):
        request = build_request(url, headers=headers, bump=i)
        start = time.perf_counter()
        uh, e = catch_request(request, opener=opener)

        if e or int(uh.code) != 200:
            # high penalty for failed pings
            latencies.append(3600.0)
            continue

        latency = time.perf_counter() - start
        latencies.append(latency)
        uh.close()

    avg_latency = sum(latencies) / len(latencies)
    server["latency"] = avg_latency

    # time.perf_counter() returns seconds in float
    server["latency_ms"] = avg_latency * 1000.0

    return server, avg_latency


def get_best_server(
    closest_servers: List[Dict[str, Any]], opener: Any
) -> Dict[str, Any]:
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
                printer(f"Server ping generated an exception: {e}", debug=True)

    if best_server is None:
        raise SpeedtestBestServerFailure(
            "Unable to determine best server via latency pings."
        )

    printer(
        f"Best server selected: {best_server.get('sponsor')} "
        f"({best_server.get('name')}) with latency {best_server.get('latency_ms'):.4f} ms",
        debug=True,
    )

    return best_server
