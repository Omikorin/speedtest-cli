"""
Manages the aggregation, formatting, and submission of speedtest results.
"""

import csv
import json
from datetime import UTC, datetime
from hashlib import md5
from io import StringIO
from typing import Any
from urllib.parse import parse_qs, urlencode
from urllib.request import OpenerDirector

from speedtest.exceptions import ShareResultsConnectFailure, ShareResultsSubmitFailure
from speedtest.http.handlers import build_opener
from speedtest.http.request import build_request, catch_request

__all__ = ["SpeedtestResults"]


class SpeedtestResults:
    """
    Class for holding the results of a speedtest, including:

    * Download speed
    * Upload speed
    * Ping/Latency to test server
    * Data about the server that the test was run against

    Additionally, this class can return result data as a dictionary or CSV,
    as well as submit a POST of the result data to the speedtest.net API
    to get a share results image link.
    """

    def __init__(
        self,
        download: float = 0.0,
        upload: float = 0.0,
        ping: float = 0.0,
        server: dict[str, Any] | None = None,
        opener: OpenerDirector | None = None,
    ):
        self.download = download
        self.upload = upload
        self.ping = ping
        self.server = server or {}

        self._share: str | None = None

        # Generate a clean ISO 8601 UTC timestamp
        self.timestamp = datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")

        self.bytes_received: int = 0
        self.bytes_sent: int = 0

        self._opener = opener or build_opener()

    def __repr__(self) -> str:
        return repr(self.to_dict())

    def share(self) -> str:
        """POST data to the speedtest.net API to obtain a share results link."""

        if self._share:
            return self._share

        download = round(self.download / 1000.0)
        ping = round(self.ping)
        upload = round(self.upload / 1000.0)

        hash_str = f"{ping}-{upload}-{download}-297aae72"
        hash_val = md5(hash_str.encode()).hexdigest()

        # We use a list of tuples instead of a dict because the speedtest API
        # expects parameters in a strict sequential order. urlencode preserves this.
        api_parameters = [
            ("recommendedserverid", self.server.get("id", "")),
            ("ping", ping),
            ("screenresolution", ""),
            ("promo", ""),
            ("download", download),
            ("screendpi", ""),
            ("upload", upload),
            ("testmethod", "http"),
            ("hash", hash_val),
            ("touchscreen", "none"),
            ("startmode", "pingselect"),
            ("accuracy", 1),
            ("bytesreceived", self.bytes_received),
            ("bytessent", self.bytes_sent),
            ("serverid", self.server.get("id", "")),
        ]

        api_data = urlencode(api_parameters).encode()
        headers = {"Referer": "https://c.speedtest.net/flash/speedtest.swf"}

        request = build_request(
            "https://www.speedtest.net/api/api.php",
            data=api_data,
            headers=headers,
        )

        f, e = catch_request(request, opener=self._opener)

        if e or not f:
            raise ShareResultsConnectFailure(e or "Failed to connect to Share API")

        # Context manager strictly handles network cleanup
        with f:
            code = int(getattr(f, "code", 500))
            if code != 200:
                raise ShareResultsSubmitFailure(f"Could not submit results. HTTP {code}")

            response = f.read()

        # Safely decode ignoring corrupted bytes
        qsargs = parse_qs(response.decode(errors="ignore"))
        resultid = qsargs.get("resultid")

        if not resultid or len(resultid) != 1:
            raise ShareResultsSubmitFailure("Could not parse result ID from API response")

        self._share = f"https://www.speedtest.net/result/{resultid[0]}.png"
        return self._share

    def to_dict(self) -> dict[str, Any]:
        """Return dictionary of result data cleanly formatted."""

        return {
            "download": self.download,
            "upload": self.upload,
            "ping": self.ping,
            "server": self.server,
            "timestamp": self.timestamp,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "share": self._share,
        }

    @staticmethod
    def csv_header(delimiter: str = ",") -> str:
        """Return CSV Headers."""

        row = [
            "Server ID",
            "Sponsor",
            "Server Name",
            "Timestamp",
            "Distance",
            "Ping",
            "Download",
            "Upload",
            "Share",
            # "IP Address",
        ]

        out = StringIO()
        writer = csv.writer(out, delimiter=delimiter, lineterminator="")
        writer.writerow(row)

        return out.getvalue()

    def csv(self, delimiter: str = ",") -> str:
        """Return data in CSV format."""

        data = self.to_dict()
        server = data.get("server", {})

        row = [
            server.get("id", ""),
            server.get("sponsor", ""),
            server.get("name", ""),
            data.get("timestamp", ""),
            server.get("d", ""),
            data.get("ping", ""),
            data.get("download", ""),
            data.get("upload", ""),
            self._share or "",
        ]

        out = StringIO()
        writer = csv.writer(out, delimiter=delimiter, lineterminator="")
        writer.writerow(row)

        return out.getvalue()

    def json(self, pretty: bool = False) -> str:
        """Return data in JSON format."""

        kwargs: dict[str, Any] = {"indent": 4, "sort_keys": True} if pretty else {}
        return json.dumps(self.to_dict(), **kwargs)
