import math
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

try:
    import gzip
except ImportError:
    gzip = None

from speedtest.exceptions import ConfigRetrievalError, SpeedtestConfigError
from speedtest.http import build_request, catch_request, get_response_stream
from speedtest.utils import printer

__all__ = ["fetch_config"]


def fetch_config(opener: Any, secure: bool = False) -> Dict[str, Any]:
    """
    Download the speedtest.net configuration, parse the XML,
    and return a standardized dictionary of settings.
    """

    headers = {"Accept-Encoding": "gzip"} if gzip else {}
    request = build_request(
        "://www.speedtest.net/speedtest-config.php",
        headers=headers,
        secure=secure,
    )

    uh, e = catch_request(request, opener=opener)
    if e:
        raise ConfigRetrievalError(e) from e

    configxml_list: List[bytes] = []
    stream = get_response_stream(uh)

    while True:
        try:
            chunk = stream.read(1024)
            configxml_list.append(chunk)
        except (OSError, EOFError) as err:
            raise ConfigRetrievalError(err) from err
        if not chunk:
            break

    stream.close()
    uh.close()

    if int(uh.code) != 200:
        return {}

    configxml = b"".join(configxml_list)
    printer(f"Config XML:\n{configxml.decode(errors='ignore')}", debug=True)

    try:
        root = ET.fromstring(configxml)
    except ET.ParseError as err:
        raise SpeedtestConfigError(f"Malformed speedtest.net configuration: {err}")

    try:
        server_config = root.find("server-config").attrib
        download = root.find("download").attrib
        upload = root.find("upload").attrib
        client = root.find("client").attrib
    except AttributeError as err:
        raise SpeedtestConfigError(f"Missing expected XML tags in config: {err}")

    ignore_servers = [
        int(i) for i in server_config.get("ignoreids", "").split(",") if i
    ]

    ratio = int(upload.get("ratio", 5))
    upload_max = int(upload.get("maxchunkcount", 50))
    up_sizes = [32768, 65536, 131072, 262144, 524288, 1048576, 7340032]
    sizes = {
        "upload": up_sizes[ratio - 1 :],
        "download": [350, 500, 750, 1000, 1500, 2000, 2500, 3000, 3500, 4000],
    }

    size_count = len(sizes["upload"])
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
    except (ValueError, KeyError):
        raise SpeedtestConfigError(
            f"Unknown location: lat={client.get('lat')} lon={client.get('lon')}"
        )

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

    printer(f"Config:\n{parsed_config}", debug=True)
    return parsed_config
