"""
Threadpool worker functions and payload data classes.
"""

import threading
import time
from urllib.request import OpenerDirector, Request, urlopen

from speedtest.exceptions import SpeedtestUploadTimeout
from speedtest.http.errors import HTTP_ERRORS, UPLOAD_ERRORS

__all__ = [
    "download_worker",
    "HTTPUploaderData",
    "upload_worker",
]

# --- Constants ---
CHUNK_SIZE_BYTES = 10240
UPLOAD_RESPONSE_TRUNCATION = 11

# A pre-calculated 10.5 KB chunk to satisfy typical urllib read calls
DUMMY_CHUNK = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 300


def download_worker(
    request: Request,
    start_time: float,
    timeout: float,
    opener: OpenerDirector | None = None,
    shutdown_event: threading.Event | None = None,
) -> int:
    """Worker function for retrieving a URL, returning total bytes downloaded."""

    _opener = opener.open if opener else urlopen
    _shutdown_event = shutdown_event or threading.Event()

    total_downloaded = 0
    deadline = start_time + timeout

    try:
        if time.monotonic() <= deadline:
            with _opener(request) as response:
                while not _shutdown_event.is_set() and time.monotonic() <= deadline:
                    chunk = response.read(CHUNK_SIZE_BYTES)
                    if not chunk:
                        break

                    total_downloaded += len(chunk)
    except HTTP_ERRORS:
        pass

    return total_downloaded


class HTTPUploaderData:
    """
    File-like object to stream dummy data for uploads with O(1) memory footprint.
    """

    def __init__(
        self,
        length: int,
        start_time: float,
        timeout: float,
        shutdown_event: threading.Event | None = None,
    ):
        self.length = length
        self.start_time = start_time
        self.timeout = timeout
        self._shutdown_event = shutdown_event or threading.Event()
        self.total_bytes_read = 0

    @property
    def deadline(self) -> float:
        """Dynamically compute the deadline so it respects external start_time updates."""

        return self.start_time + self.timeout

    def read(self, n: int = -1) -> bytes:
        """Yield dynamic chunks of dummy data until length or timeout is reached."""

        if time.monotonic() > self.deadline or self._shutdown_event.is_set():
            raise SpeedtestUploadTimeout()

        remaining = self.length - self.total_bytes_read
        if remaining <= 0:
            return b""

        # If n is negative or larger than remaining, read everything left.
        read_size = remaining if (n < 0 or n > remaining) else n

        if read_size <= len(DUMMY_CHUNK):
            chunk = DUMMY_CHUNK[:read_size]
        else:
            chunk = b"A" * read_size

        self.total_bytes_read += len(chunk)
        return chunk

    def __len__(self) -> int:
        return self.length


def upload_worker(
    request: Request,
    payload_data: HTTPUploaderData,
    timeout: float,
    opener: OpenerDirector | None = None,
    shutdown_event: threading.Event | None = None,
) -> int:
    """Worker function for putting a URL, returning total bytes uploaded."""

    _opener = opener.open if opener else urlopen
    _shutdown_event = shutdown_event or threading.Event()

    request.data = payload_data
    request.method = "POST"

    try:
        if time.monotonic() <= payload_data.deadline and not _shutdown_event.is_set():
            with _opener(request) as response:
                response.read(UPLOAD_RESPONSE_TRUNCATION)
            return payload_data.total_bytes_read

        return 0
    except UPLOAD_ERRORS:
        return payload_data.total_bytes_read
