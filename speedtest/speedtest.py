import math
import os
import re
import threading
import time
import timeit
import xml.etree.ElementTree as ET
from queue import Queue
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

try:
    import gzip

    GZIP_BASE = gzip.GzipFile
except ImportError:
    gzip = None
    GZIP_BASE = object

from speedtest.exceptions import (
    ConfigRetrievalError,
    InvalidServerIDType,
    InvalidSpeedtestMiniServer,
    NoMatchedServers,
    ServersRetrievalError,
    SpeedtestBestServerFailure,
    SpeedtestConfigError,
    SpeedtestMiniConnectFailure,
    SpeedtestServersError,
)
from speedtest.http import (
    HTTP_ERRORS,
    FakeShutdownEvent,
    HTTPDownloader,
    HTTPUploader,
    HTTPUploaderData,
    SpeedtestHTTPConnection,
    SpeedtestHTTPSConnection,
    build_opener,
    build_request,
    build_user_agent,
    catch_request,
    get_response_stream,
)
from speedtest.results import SpeedtestResults
from speedtest.utils import distance, do_nothing, printer


class Speedtest:
    """Class for performing standard speedtest.net testing operations."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        source_address: Optional[str] = None,
        timeout: float = 10.0,
        secure: bool = False,
        shutdown_event: Any = None,
    ):
        self.config: Dict[str, Any] = {}

        self._source_address = source_address
        self._timeout = timeout
        self._opener = build_opener(source_address, timeout)

        self._secure = secure
        self._shutdown_event = shutdown_event or FakeShutdownEvent()

        self.get_config()
        if config is not None:
            self.config.update(config)

        self.servers: Dict[float, List[Dict[str, Any]]] = {}
        self.closest: List[Dict[str, Any]] = []
        self._best: Dict[str, Any] = {}

        self.results = SpeedtestResults(
            client=self.config.get("client", {}),
            opener=self._opener,
            secure=secure,
        )

    @property
    def best(self) -> Dict[str, Any]:
        if not self._best:
            self.get_best_server()
        return self._best

    def get_config(self) -> Dict[str, Any]:
        """Download the speedtest.net configuration and return the needed data."""

        headers = {"Accept-Encoding": "gzip"} if gzip else {}
        request = build_request(
            "://www.speedtest.net/speedtest-config.php",
            headers=headers,
            secure=self._secure,
        )

        uh, e = catch_request(request, opener=self._opener)
        if e:
            raise ConfigRetrievalError(e)

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
            # times = root.find('times').attrib
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

        counts = {
            "upload": upload_count,
            "download": int(download.get("threadsperurl", 4)),
        }

        threads = {
            "upload": int(upload.get("threads", 4)),
            "download": int(server_config.get("threadcount", 4)) * 2,
        }

        length = {
            "upload": int(upload.get("testlength", 10)),
            "download": int(download.get("testlength", 10)),
        }

        self.config.update(
            {
                "client": client,
                "ignore_servers": ignore_servers,
                "sizes": sizes,
                "counts": counts,
                "threads": threads,
                "length": length,
                "upload_max": upload_count * size_count,
            }
        )

        try:
            self.lat_lon = (float(client["lat"]), float(client["lon"]))
        except (ValueError, KeyError):
            raise SpeedtestConfigError(
                f"Unknown location: lat={client.get('lat')} lon={client.get('lon')}"
            )

        printer(f"Config:\n{self.config}", debug=True)
        return self.config

    def get_servers(
        self, servers: Optional[List[int]] = None, exclude: Optional[List[int]] = None
    ) -> Dict[float, List[Dict[str, Any]]]:
        """Retrieve the list of speedtest.net servers, optionally filtered."""
        servers = servers or []
        exclude = exclude or []
        self.servers.clear()

        # validate provided lists
        for server_list in (servers, exclude):
            for i, s in enumerate(server_list):
                try:
                    server_list[i] = int(s)
                except ValueError:
                    raise InvalidServerIDType(
                        f"{s} is an invalid server type, must be int"
                    )

        urls = [
            "://www.speedtest.net/speedtest-servers-static.php",
            "http://c.speedtest.net/speedtest-servers-static.php",
            "://www.speedtest.net/speedtest-servers.php",
            "http://c.speedtest.net/speedtest-servers.php",
        ]

        headers = {"Accept-Encoding": "gzip"} if gzip else {}
        errors = []

        for url in urls:
            try:
                thread_count = self.config.get("threads", {}).get("download", 8)
                request = build_request(
                    f"{url}?threads={thread_count}",
                    headers=headers,
                    secure=self._secure,
                )

                uh, e = catch_request(request, opener=self._opener)
                if e:
                    errors.append(str(e))
                    raise ServersRetrievalError()

                stream = get_response_stream(uh)
                serversxml_list: List[bytes] = []

                while True:
                    try:
                        chunk = stream.read(1024)
                        serversxml_list.append(chunk)
                    except (OSError, EOFError) as err:
                        raise ServersRetrievalError(err) from err
                    if not chunk:
                        break

                stream.close()
                uh.close()

                if int(uh.code) != 200:
                    raise ServersRetrievalError()

                serversxml = b"".join(serversxml_list)
                printer(
                    f"Servers XML:\n{serversxml.decode(errors='ignore')}", debug=True
                )

                try:
                    root = ET.fromstring(serversxml)
                    elements = root.iter("server")
                except ET.ParseError as err:
                    raise SpeedtestServersError(
                        f"Malformed speedtest.net server list: {err}"
                    )

                for server in elements:
                    attrib = server.attrib
                    server_id = int(attrib.get("id", 0))

                    if servers and server_id not in servers:
                        continue

                    if (
                        server_id in self.config.get("ignore_servers", [])
                        or server_id in exclude
                    ):
                        continue

                    try:
                        d = distance(
                            self.lat_lon,
                            (float(attrib.get("lat", 0)), float(attrib.get("lon", 0))),
                        )
                    except (ValueError, TypeError):
                        continue

                    attrib["d"] = d
                    self.servers.setdefault(d, []).append(attrib)

                break  # successful fetch, break out of URL loop
            # TODO: simplify

            except ServersRetrievalError:
                continue

        if (servers or exclude) and not self.servers:
            raise NoMatchedServers()

        return self.servers

    def set_mini_server(self, server: str) -> List[Dict[str, Any]]:
        """Set a link to a speedtest mini server instead of querying a list."""

        urlparts = urlparse(server)
        name, ext = os.path.splitext(urlparts.path)

        url = os.path.dirname(server) if ext else server

        request = build_request(url)
        uh, e = catch_request(request, opener=self._opener)
        if e:
            raise SpeedtestMiniConnectFailure(f"Failed to connect to {server}")

        text = uh.read()
        uh.close()

        extension = re.findall(
            r'upload_?[Ee]xtension: "([^"]+)"', text.decode(errors="ignore")
        )
        if not extension:
            for ext_type in ["php", "asp", "aspx", "jsp"]:
                try:
                    f = self._opener.open(f"{url}/speedtest/upload.{ext_type}")
                    data = f.read().strip().decode(errors="ignore")
                    if (
                        f.code == 200
                        and len(data.splitlines()) == 1
                        and re.match(r"size=[0-9]", data)
                    ):
                        extension = [ext_type]
                        break
                except Exception:
                    pass

        if not urlparts or not extension:
            raise InvalidSpeedtestMiniServer(f"Invalid Speedtest Mini Server: {server}")

        mini_server = {
            "sponsor": "Speedtest Mini",
            "name": urlparts.netloc,
            "d": 0,
            "url": f"{url.rstrip('/')}/speedtest/upload.{extension[0]}",
            "latency": 0,
            "id": 0,
        }

        self.servers = [mini_server]  # type: ignore
        return self.servers  # type: ignore

    def get_closest_servers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Limit servers to the closest ones based on geographic distance."""

        if not self.servers:
            self.get_servers()

        self.closest.clear()

        for d in sorted(self.servers.keys()):
            for s in self.servers[d]:
                self.closest.append(s)
                if len(self.closest) == limit:
                    break
            else:
                continue
            break

        printer(f"Closest Servers:\n{self.closest}", debug=True)
        return self.closest

    def get_best_server(
        self, servers: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Perform a ping to determine which server has the lowest latency."""

        if not servers:
            if not self.closest:
                self.get_closest_servers()
            servers = self.closest

        source_address_tuple = (
            (self._source_address, 0) if self._source_address else None
        )
        user_agent = build_user_agent()
        results: Dict[float, Dict[str, Any]] = {}

        for server in servers:
            cum: List[float] = []
            url = os.path.dirname(server.get("url", ""))
            stamp = int(time.time() * 1000)
            latency_url = f"{url}/latency.txt?x={stamp}"

            for i in range(3):
                this_latency_url = f"{latency_url}.{i}"
                printer(f"GET {this_latency_url}", debug=True)
                urlparts = urlparse(latency_url)

                try:
                    if urlparts.scheme == "https":
                        h = SpeedtestHTTPSConnection(
                            urlparts.netloc, source_address=source_address_tuple
                        )
                    else:
                        h = SpeedtestHTTPConnection(
                            urlparts.netloc, source_address=source_address_tuple
                        )

                    headers = {"User-Agent": user_agent}
                    path = (
                        f"{urlparts.path}?{urlparts.query}"
                        if urlparts.query
                        else urlparts.path
                    )

                    start = timeit.default_timer()
                    h.request("GET", path, headers=headers)
                    r = h.getresponse()
                    total = timeit.default_timer() - start
                except HTTP_ERRORS as e:
                    printer(f"ERROR: {e!r}", debug=True)
                    cum.append(3600.0)
                    continue

                text = r.read(9)
                if int(r.status) == 200 and text == b"test=test":
                    cum.append(total)
                else:
                    cum.append(3600.0)
                h.close()

            avg = round((sum(cum) / 6) * 1000.0, 3)
            results[avg] = server

        try:
            fastest = sorted(results.keys())[0]
        except IndexError:
            raise SpeedtestBestServerFailure(
                "Unable to connect to servers to test latency."
            )

        best = results[fastest]
        best["latency"] = fastest

        self.results.ping = fastest
        self.results.server = best
        self._best.update(best)

        printer(f"Best Server:\n{best}", debug=True)
        return best

    def download(
        self, callback: Callable = do_nothing, threads: Optional[int] = None
    ) -> float:
        """Test download speed against speedtest.net."""

        urls = []
        base_url = os.path.dirname(self.best["url"])

        for size in self.config["sizes"]["download"]:
            for _ in range(self.config["counts"]["download"]):
                urls.append(f"{base_url}/random{size}x{size}.jpg")

        request_count = len(urls)
        requests = [
            build_request(url, bump=i, secure=self._secure)
            for i, url in enumerate(urls)
        ]
        max_threads = threads or self.config["threads"]["download"]
        in_flight = {"threads": 0}

        def producer(q: Queue, reqs: List[Any], req_count: int) -> None:
            for i, request in enumerate(reqs):
                thread = HTTPDownloader(
                    i,
                    request,
                    start,
                    self.config["length"]["download"],
                    opener=self._opener,
                    shutdown_event=self._shutdown_event,
                )
                while in_flight["threads"] >= max_threads:
                    time.sleep(0.001)

                thread.start()
                q.put(thread, True)
                in_flight["threads"] += 1
                callback(i, req_count, start=True)

        finished: List[float] = []

        def consumer(q: Queue, req_count: int) -> None:
            while len(finished) < req_count:
                thread = q.get(True)
                while thread.is_alive():
                    thread.join(timeout=0.001)

                in_flight["threads"] -= 1
                finished.append(sum(thread.result))
                callback(thread.i, req_count, end=True)

        q: Queue = Queue(max_threads)
        prod_thread = threading.Thread(
            target=producer, args=(q, requests, request_count)
        )
        cons_thread = threading.Thread(target=consumer, args=(q, request_count))

        start = timeit.default_timer()
        prod_thread.start()
        cons_thread.start()

        while prod_thread.is_alive():
            prod_thread.join(timeout=0.001)
        while cons_thread.is_alive():
            cons_thread.join(timeout=0.001)

        stop = timeit.default_timer()
        self.results.bytes_received = sum(finished)
        self.results.download = (self.results.bytes_received / (stop - start)) * 8.0

        if self.results.download > 100000:
            self.config["threads"]["upload"] = 8

        return self.results.download

    def upload(
        self,
        callback: Callable = do_nothing,
        pre_allocate: bool = True,
        threads: Optional[int] = None,
    ) -> float:
        """Test upload speed against speedtest.net."""

        sizes = [
            size
            for size in self.config["sizes"]["upload"]
            for _ in range(self.config["counts"]["upload"])
        ]

        request_count = self.config["upload_max"]
        requests = []

        for i, size in enumerate(sizes):
            # We set ``0`` for ``start`` and handle setting the actual
            # ``start`` in ``HTTPUploader`` to get better measurements
            data = HTTPUploaderData(
                size,
                0,
                self.config["length"]["upload"],
                shutdown_event=self._shutdown_event,
            )
            if pre_allocate:
                data.pre_allocate()

            headers = {"Content-length": str(size)}
            req = build_request(
                self.best["url"], data, secure=self._secure, headers=headers
            )
            requests.append((req, size))

        max_threads = threads or self.config["threads"]["upload"]
        in_flight = {"threads": 0}

        def producer(q: Queue, reqs: List[Tuple[Any, int]], req_count: int) -> None:
            for i, request in enumerate(reqs[:req_count]):
                thread = HTTPUploader(
                    i,
                    request[0],
                    start,
                    request[1],
                    self.config["length"]["upload"],
                    opener=self._opener,
                    shutdown_event=self._shutdown_event,
                )
                while in_flight["threads"] >= max_threads:
                    time.sleep(0.001)

                thread.start()
                q.put(thread, True)
                in_flight["threads"] += 1
                callback(i, req_count, start=True)

        finished: List[float] = []

        def consumer(q: Queue, req_count: int) -> None:
            while len(finished) < req_count:
                thread = q.get(True)
                while thread.is_alive():
                    thread.join(timeout=0.001)

                in_flight["threads"] -= 1
                finished.append(thread.result)
                callback(thread.i, req_count, end=True)

        q: Queue = Queue(max_threads)
        prod_thread = threading.Thread(
            target=producer, args=(q, requests, request_count)
        )
        cons_thread = threading.Thread(target=consumer, args=(q, request_count))

        start = timeit.default_timer()
        prod_thread.start()
        cons_thread.start()

        while prod_thread.is_alive():
            prod_thread.join(timeout=0.1)
        while cons_thread.is_alive():
            cons_thread.join(timeout=0.1)

        stop = timeit.default_timer()
        self.results.bytes_sent = sum(finished)
        self.results.upload = (self.results.bytes_sent / (stop - start)) * 8.0
        return self.results.upload
