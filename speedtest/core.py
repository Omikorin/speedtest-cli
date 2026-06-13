import threading
from typing import Any

from speedtest.config import fetch_config
from speedtest.exceptions import NoMatchedServers
from speedtest.http.handlers import build_opener
from speedtest.results import SpeedtestResults
from speedtest.servers import fetch_servers, get_best_server
from speedtest.transfer import run_download_test, run_upload_test

__all__ = ["Speedtest"]


class Speedtest:
    """Class for performing standard speedtest.net testing operations."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        source_address: str | None = None,
        timeout: float = 10.0,
        shutdown_event: Any = None,
        threads: int | None = None,
    ):
        self._source_address = source_address
        self._timeout = timeout
        self._shutdown_event = shutdown_event or threading.Event()
        self._threads = threads

        self._opener = build_opener(source_address, timeout)

        # fetch default configuration and merge optional overrides
        self.config = fetch_config(self._opener)
        if config is not None:
            self.config.update(config)

        self.lat_lon = self.config.get("lat_lon", (0.0, 0.0))

        # core state data structures
        self.servers: dict[float, list[dict[str, Any]]] = {}
        self.closest: list[dict[str, Any]] = []
        self._best: dict[str, Any] = {}

        self.results = SpeedtestResults(
            client=self.config.get("client", {}),
            opener=self._opener,
        )

    @property
    def best(self) -> dict[str, Any]:
        """Lazy-loaded property to retrieve the best available server."""

        if not self._best:
            self.get_best_server()
        return self._best

    def get_servers(
        self, servers: list[int] | None = None
    ) -> dict[float, list[dict[str, Any]]]:
        """
        Fetch the server list from speedtest.net, sort them by distance,
        and optionally filter down to a specified subset of IDs.
        """

        ignore = self.config.get("ignore_servers", [])

        self.servers = fetch_servers(
            opener=self._opener,
            lat_lon=self.lat_lon,
            ignore_servers=ignore,
        )

        # flatten the distance-grouped dict into a clean linear list sorted by proximity
        sorted_distances = sorted(self.servers.keys())
        self.closest = [
            server for distance in sorted_distances for server in self.servers[distance]
        ]

        # filter by specific server IDs if requested
        if servers:
            target_ids = {int(s) for s in servers}
            self.closest = [
                s for s in self.closest if int(s.get("id", 0)) in target_ids
            ]

            if not self.closest:
                raise NoMatchedServers(f"No servers matched the criteria: {servers}")

        return self.servers

    def get_best_server(self, limit: int = 5) -> dict[str, Any]:
        """Determine the lowest-latency server by pinging the top `limit` closest options."""

        if not self.closest:
            self.get_servers()

        # isolate the closest N servers to avoid wasting execution time pinging distant servers
        candidates = self.closest[:limit]

        self._best = get_best_server(candidates, self._opener)

        self.results.server = self._best
        self.results.ping = self._best["latency_ms"]

        return self._best

    def download(self) -> float:
        """Test concurrent download speed against the chosen optimal server."""

        bytes_received, download_speed = run_download_test(
            best_server_url=self.best["url"],
            config=self.config,
            opener=self._opener,
            shutdown_event=self._shutdown_event,
            threads=self._threads,
        )

        self.results.bytes_received = bytes_received
        self.results.download = download_speed

        return self.results.download

    def upload(self, pre_allocate: bool = True) -> float:
        """Test concurrent upload speed against the chosen optimal server."""

        bytes_sent, upload_speed = run_upload_test(
            best_server_url=self.best["url"],
            config=self.config,
            opener=self._opener,
            shutdown_event=self._shutdown_event,
            pre_allocate=pre_allocate,
            threads=self._threads,
        )

        self.results.bytes_sent = bytes_sent
        self.results.upload = upload_speed

        return self.results.upload
