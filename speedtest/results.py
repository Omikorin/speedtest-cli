import csv
import json
from datetime import datetime, timezone
from hashlib import md5
from io import StringIO
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlencode

from speedtest.exceptions import ShareResultsConnectFailure, ShareResultsSubmitFailure
from speedtest.http import build_opener, build_request, catch_request

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
        server: Optional[Dict[str, Any]] = None,
        client: Optional[Dict[str, str]] = None,
        opener: Any = None,
        secure: bool = False,
    ):
        self.download = download
        self.upload = upload
        self.ping = ping
        self.server = server or {}
        self.client = client or {}

        self._share: Optional[str] = None

        # generate a clean ISO 8601 UTC timestamp
        self.timestamp = (
            datetime.now(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )

        self.bytes_received = 0
        self.bytes_sent = 0

        self._opener = opener or build_opener()
        self._secure = secure

    def __repr__(self) -> str:
        return repr(self.dict())

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
        headers = {"Referer": "http://c.speedtest.net/flash/speedtest.swf"}

        request = build_request(
            "://www.speedtest.net/api/api.php",
            data=api_data,
            headers=headers,
            secure=self._secure,
        )

        f, e = catch_request(request, opener=self._opener)
        if e:
            raise ShareResultsConnectFailure(e)

        try:
            # capture code before reading to avoid UnboundLocalError
            code = int(f.code)
            response = f.read()
        finally:
            f.close()

        if code != 200:
            raise ShareResultsSubmitFailure(f"Could not submit results. HTTP {code}")

        qsargs = parse_qs(response.decode())
        resultid = qsargs.get("resultid")

        if not resultid or len(resultid) != 1:
            raise ShareResultsSubmitFailure(
                "Could not parse result ID from API response"
            )

        self._share = f"https://www.speedtest.net/result/{resultid[0]}.png"
        return self._share

    def dict(self) -> Dict[str, Any]:
        """Return dictionary of result data."""

        return {
            "download": self.download,
            "upload": self.upload,
            "ping": self.ping,
            "server": self.server,
            "timestamp": self.timestamp,
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "share": self._share,
            "client": self.client,
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
            "IP Address",
        ]

        out = StringIO()

        writer = csv.writer(out, delimiter=delimiter, lineterminator="")
        writer.writerow(row)

        return out.getvalue()

    def csv(self, delimiter: str = ",") -> str:
        """Return data in CSV format."""

        data = self.dict()

        row = [
            data["server"].get("id", ""),
            data["server"].get("sponsor", ""),
            data["server"].get("name", ""),
            data["timestamp"],
            data["server"].get("d", ""),
            data["ping"],
            data["download"],
            data["upload"],
            self._share or "",
            self.client.get("ip", ""),
        ]

        out = StringIO()
        writer = csv.writer(out, delimiter=delimiter, lineterminator="")
        writer.writerow(row)

        return out.getvalue()

    def json(self, pretty: bool = False) -> str:
        """Return data in JSON format."""

        kwargs: Dict[str, Any] = {"indent": 4, "sort_keys": True} if pretty else {}
        return json.dumps(self.dict(), **kwargs)
