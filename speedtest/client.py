import threading
from operator import attrgetter

from speedtest.engine.config import get_config
from speedtest.engine.results import SpeedtestResults
from speedtest.engine.servers import get_best_server
from speedtest.engine.transfer import run_download_test, run_upload_test
from speedtest.exceptions import NoMatchedServer, SpeedtestCLIError
from speedtest.http.handlers import build_opener
from speedtest.models import Server

__all__ = ["Speedtest"]


class Speedtest:
    """Class for performing standard speedtest.net testing operations."""

    def __init__(
        self,
        source_address: str | None = None,
        timeout: float = 10.0,
        shutdown_event: threading.Event | None = None,
        threads: int | None = None,
    ):
        self._shutdown_event = shutdown_event or threading.Event()
        self._threads = threads

        self._opener = build_opener(source_address, timeout)

        # Fetch default configuration and safely merge optional overrides
        self.config = get_config()

        # Core state data structures
        self.servers: list[Server] = []
        self.sorted_servers: list[Server] = []
        self.closest_servers: list[Server] = []
        self._best: Server | None = None
        self._best_latency: float = 3600.0

        self.results = SpeedtestResults(
            opener=self._opener,
        )

    @property
    def best(self) -> Server:
        """Lazy-loaded property to retrieve the best available server."""

        if not self._best:
            self.get_best_server()
        return self._best  # type: ignore

    def get_sorted_servers(self) -> list[Server]:
        """
        Sorts a list of servers by their pre-calculated distance.
        """

        self.sorted_servers = sorted(self.servers, key=attrgetter("distance"))

        return self.sorted_servers

    def get_closest_servers(self, limit: int) -> list[Server]:
        """
        Returns the top N closest servers.
        """

        self.closest_servers = self.sorted_servers[:limit]

        return self.closest_servers

    def get_servers(self, server: int | None = None, limit: int = 5) -> list[Server]:
        """
        Fetch the server list from speedtest.net, sort them by distance,
        and optionally filter down to a specific server ID.
        """

        self.servers = self.config.servers.copy()
        self.get_sorted_servers()
        self.get_closest_servers(limit)

        # Filter by a specific server ID if requested
        if server is not None:
            self.closest_servers = [srv for srv in self.servers if srv.id == server]

            if not self.closest_servers:
                raise NoMatchedServer(f"No server matched the ID: {server}")

        return self.servers

    def get_best_server(self, limit: int = 5) -> Server:
        """Determine the lowest-latency server by pinging the top `limit` closest options."""

        if not self.closest_servers:
            self.get_servers(limit)

        if not self.closest_servers:
            raise SpeedtestCLIError("No servers available to test against.")

        self._best, self._best_latency = get_best_server(self.closest_servers, self._opener)

        if not self._best:
            raise SpeedtestCLIError("Failed to identify a valid best server.")

        self.results.server = self._best
        self.results.ping = self._best_latency

        return self._best

    def download(self) -> float:
        """Test concurrent download speed against the chosen optimal server."""

        best_url = self.best.url
        if not best_url:
            raise SpeedtestCLIError("The best selected server is missing a valid URL.")

        bytes_received, download_speed = run_download_test(
            best_server_url=best_url,
            opener=self._opener,
            shutdown_event=self._shutdown_event,
            threads=self._threads,
        )

        self.results.bytes_received = bytes_received
        self.results.download = download_speed

        return self.results.download

    def upload(self) -> float:
        """Test concurrent upload speed against the chosen optimal server."""

        best_url = self.best.url
        if not best_url:
            raise SpeedtestCLIError("The best selected server is missing a valid URL.")

        bytes_sent, upload_speed = run_upload_test(
            best_server_url=best_url,
            opener=self._opener,
            shutdown_event=self._shutdown_event,
            threads=self._threads,
        )

        self.results.bytes_sent = bytes_sent
        self.results.upload = upload_speed

        return self.results.upload
