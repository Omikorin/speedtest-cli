"""
Retrieves and parses the core configuration XML from speedtest.net.
"""

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

    client_node = root.find("client")

    if not all([
        client_node is not None,
    ]):
        raise SpeedtestConfigError("Missing expected XML tags in the config payload.")

    client = client_node.attrib  # type: ignore

    try:
        lat_lon = (float(client["lat"]), float(client["lon"]))
    except (ValueError, KeyError) as err:
        raise SpeedtestConfigError(
            f"Unknown location: lat={client.get('lat')} lon={client.get('lon')}"
        ) from err

    parsed_config = {
        "client": client,
        "lat_lon": lat_lon,
    }

    logger.debug(f"Config:\n{parsed_config}")
    return parsed_config
