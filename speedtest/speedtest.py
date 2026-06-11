from typing import Any, Callable, Dict, List, Optional

from speedtest.config import fetch_config
from speedtest.http import (
    FakeShutdownEvent,
    build_opener,
)
from speedtest.results import SpeedtestResults
from speedtest.servers import fetch_servers, get_best_server
from speedtest.transfer import run_download_test, run_upload_test
from speedtest.utils import do_nothing

try:
    import gzip

    GZIP_BASE = gzip.GzipFile
except ImportError:
    gzip = None
    GZIP_BASE = object


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

        bytes_received, download_speed = run_download_test(
            best_server_url=self.best["url"],
            config=self.config,
            opener=self._opener,
            secure=self._secure,
            shutdown_event=self._shutdown_event,
            callback=callback,
            threads=threads,
        )

        self.results.bytes_received = bytes_received
        self.results.download = download_speed

        return self.results.download

    def upload(
        self,
        callback: Callable = do_nothing,
        pre_allocate: bool = True,
        threads: Optional[int] = None,
    ) -> float:
        """Test upload speed against speedtest.net."""

        bytes_sent, upload_speed = run_upload_test(
            best_server_url=self.best["url"],
            config=self.config,
            opener=self._opener,
            secure=self._secure,
            shutdown_event=self._shutdown_event,
            callback=callback,
            pre_allocate=pre_allocate,
            threads=threads,
        )

        self.results.bytes_sent = bytes_sent
        self.results.upload = upload_speed

        return self.results.upload
