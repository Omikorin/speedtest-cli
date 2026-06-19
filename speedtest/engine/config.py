"""
Retrieves and parses the core configuration XML from speedtest.net.
"""

import math
import xml.etree.ElementTree as ET
from typing import Any

from speedtest.exceptions import ConfigRetrievalError, SpeedtestConfigError
from speedtest.http.request import build_request, catch_request
from speedtest.http.response import get_response_stream
from speedtest.utils.logger import logger

__all__ = ["fetch_config"]


def fetch_config(opener: Any) -> dict[str, Any]:
    """
    Download the speedtest.net configuration, parse the XML,
    and return a standardized dictionary of settings.
    """

    headers = {"Accept-Encoding": "gzip"}
    request = build_request(
        "https://www.speedtest.net/speedtest-config.php",
        headers=headers,
    )

    uh, e = catch_request(request, opener=opener)
    if e or not uh:
        raise ConfigRetrievalError(e) from e

    with uh:
        if int(getattr(uh, "code", 200)) != 200:
            raise ConfigRetrievalError(f"HTTP Error {uh.code} while fetching config")  # type: ignore

        try:
            with get_response_stream(uh) as stream:
                configxml = stream.read()
        except (OSError, EOFError) as err:
            raise ConfigRetrievalError(err) from err

    logger.debug(f"Config XML:\n{configxml.decode(errors='ignore')}")

    try:
        root = ET.fromstring(configxml)
    except ET.ParseError as err:
        raise SpeedtestConfigError(f"Malformed speedtest.net configuration: {err}")

    server_config_node = root.find("server-config")
    download_node = root.find("download")
    upload_node = root.find("upload")
    client_node = root.find("client")

    if not all(
        [
            server_config_node is not None,
            download_node is not None,
            upload_node is not None,
            client_node is not None,
        ]
    ):
        raise SpeedtestConfigError("Missing expected XML tags in the config payload.")

    server_config = server_config_node.attrib  # type: ignore
    download = download_node.attrib  # type: ignore
    upload = upload_node.attrib  # type: ignore
    client = client_node.attrib  # type: ignore

    ignore_servers = [int(i) for i in server_config.get("ignoreids", "").split(",") if i.strip()]

    ratio = int(upload.get("ratio", 5))
    upload_max = int(upload.get("maxchunkcount", 50))
    up_sizes = [32768, 65536, 131072, 262144, 524288, 1048576, 7340032]

    slice_idx = max(0, ratio - 1)

    sizes = {
        "upload": up_sizes[slice_idx:],
        "download": [350, 500, 750, 1000, 1500, 2000, 2500, 3000, 3500, 4000],
    }

    size_count = len(sizes["upload"])
    if size_count == 0:
        raise SpeedtestConfigError("Upload size list evaluated to empty based on configured ratio.")

    upload_count = math.ceil(upload_max / size_count)

    counts = {"upload": upload_count, "download": int(download.get("threadsperurl", 4))}

    threads = {
        "upload": int(upload.get("threads", 4)),
        "download": int(server_config.get("threadcount", 4)) * 2,
    }

    length = {
        "upload": int(upload.get("testlength", 10)),
        "download": int(download.get("testlength", 10)),
    }

    try:
        lat_lon = (float(client["lat"]), float(client["lon"]))
    except (ValueError, KeyError) as err:
        raise SpeedtestConfigError(
            f"Unknown location: lat={client.get('lat')} lon={client.get('lon')}"
        ) from err

    parsed_config = {
        "client": client,
        "ignore_servers": ignore_servers,
        "sizes": sizes,
        "counts": counts,
        "threads": threads,
        "length": length,
        "upload_max": upload_count * size_count,
        "lat_lon": lat_lon,
    }

    logger.debug(f"Config:\n{parsed_config}")
    return parsed_config
