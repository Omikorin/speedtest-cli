import os
import threading
import time
import timeit
from queue import Queue
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import gzip

    GZIP_BASE = gzip.GzipFile
except ImportError:
    gzip = None
    GZIP_BASE = object

from speedtest.config import fetch_config
from speedtest.http import (
    FakeShutdownEvent,
    HTTPDownloader,
    HTTPUploader,
    HTTPUploaderData,
    build_opener,
    build_request,
)
from speedtest.results import SpeedtestResults
from speedtest.servers import fetch_servers, get_best_server
from speedtest.utils import do_nothing


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

        self.config = fetch_config(self._opener, self._secure)
        if config is not None:
            self.config.update(config)

        self.lat_lon = self.config.get("lat_lon", (0.0, 0.0))

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

    def get_servers(
        self, servers: Optional[List[int]] = None
    ) -> Dict[float, List[Dict[str, Any]]]:
        """Fetch and set the server list based on distance."""

        ignore = self.config.get("ignore_servers", [])

        self.servers = fetch_servers(
            opener=self._opener,
            lat_lon=self.lat_lon,
            ignore_servers=ignore,
            secure=self._secure,
        )

        sorted_distances = sorted(self.servers.keys())
        self.closest = []
        for d in sorted_distances:
            for s in self.servers[d]:
                self.closest.append(s)

        # optionally, filter by specific server IDs if requested
        if servers:
            self.closest = [s for s in self.closest if int(s["id"]) in servers]

        return self.servers

    def get_best_server(self, limit: int = 5) -> Dict[str, Any]:
        """Determine the best server by pinging the top `limit` closest servers."""

        if not self.closest:
            self.get_servers()

        # only ping the top N closest servers to save time
        candidates = self.closest[:limit]

        self._best = get_best_server(candidates, self._opener)
        self.results.server = self._best

        return self._best

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
