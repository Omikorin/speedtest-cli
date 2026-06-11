import csv
import json
from datetime import datetime, timezone
from hashlib import md5
from io import StringIO
from typing import Any, Optional
from urllib.parse import parse_qs

from speedtest.exceptions import ShareResultsConnectFailure, ShareResultsSubmitFailure
from speedtest.http import build_opener, build_request, catch_request


class SpeedtestResults:
    """Class for holding the results of a speedtest, including:

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
        server: Optional[dict[str, Any]] = None,
        client: Optional[dict[str, str]] = None,
        opener: Any = None,
        secure: bool = False,
    ):
        self.download = download
        self.upload = upload
        self.ping = ping
        self.server = server or {}
        self.client = client or {}

        self._share: Optional[str] = None

        self.timestamp = (
            f"{datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}Z"
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

        # Build the request to send results back to speedtest.net.
        # We use a list instead of a dict because the API expects parameters
        # in a strict sequential order.
        api_data = [
            f"recommendedserverid={self.server.get('id', '')}",
            f"ping={ping}",
            "screenresolution=",
            "promo=",
            f"download={download}",
            "screendpi=",
            f"upload={upload}",
            "testmethod=http",
            f"hash={hash_val}",
            "touchscreen=none",
            "startmode=pingselect",
            "accuracy=1",
            f"bytesreceived={self.bytes_received}",
            f"bytessent={self.bytes_sent}",
            f"serverid={self.server.get('id', '')}",
        ]

        headers = {"Referer": "http://c.speedtest.net/flash/speedtest.swf"}
        request = build_request(
            "://www.speedtest.net/api/api.php",
            data="&".join(api_data).encode(),
            headers=headers,
            secure=self._secure,
        )

        f, e = catch_request(request, opener=self._opener)
        if e:
            raise ShareResultsConnectFailure(e)

        try:
            response = f.read()
            code = f.code
        finally:
            f.close()

        if int(code) != 200:
            raise ShareResultsSubmitFailure("Could not submit results to speedtest.net")

        qsargs = parse_qs(response.decode())
        resultid = qsargs.get("resultid")

        if not resultid or len(resultid) != 1:
            raise ShareResultsSubmitFailure("Could not submit results to speedtest.net")

        self._share = f"https://www.speedtest.net/result/{resultid[0]}.png"
        return self._share

    def dict(self) -> dict[str, Any]:
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
        out = StringIO()
        writer = csv.writer(out, delimiter=delimiter, lineterminator="")

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

        writer.writerow(row)
        return out.getvalue()

    def json(self, pretty: bool = False) -> str:
        """Return data in JSON format."""

        kwargs: dict[str, Any] = {"indent": 4, "sort_keys": True} if pretty else {}
        return json.dumps(self.dict(), **kwargs)
