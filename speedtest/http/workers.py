"""
Threadpool worker functions and payload data classes.
"""

import threading
import time
import urllib.error
import urllib.request

from speedtest.exceptions import SpeedtestUploadTimeout

# --- Constants ---
CHUNK_SIZE_BYTES = 10240
UPLOAD_RESPONSE_TRUNCATION = 11

# A pre-calculated 10.5 KB chunk to satisfy typical urllib read calls
DUMMY_CHUNK = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 300

__all__ = [
    "HTTPUploaderData",
    "download_worker",
    "upload_worker",
]


def download_worker(
    request: urllib.request.Request,
    start_time: float,
    timeout: float,
    shutdown_event: threading.Event | None = None,
) -> int:
    """Worker function for retrieving a URL, returning total bytes downloaded."""

    total_downloaded = 0
    deadline = start_time + timeout

    remaining_time = deadline - time.monotonic()

    if remaining_time <= 0 or (shutdown_event and shutdown_event.is_set()):
        return 0

    try:
        with urllib.request.urlopen(request, timeout=remaining_time) as response:
            while time.monotonic() <= deadline:
                if shutdown_event and shutdown_event.is_set():
                    break

                chunk = response.read(CHUNK_SIZE_BYTES)
                if not chunk:
                    break

                total_downloaded += len(chunk)

    except (urllib.error.URLError, TimeoutError, OSError):
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
        self._shutdown_event = shutdown_event
        self.total_bytes_read = 0

    @property
    def deadline(self) -> float:
        """Dynamically compute the deadline so it respects external start_time updates."""

        return self.start_time + self.timeout

    def read(self, n: int = -1) -> bytes:
        """Yield dynamic chunks of dummy data until length or timeout is reached."""

        if time.monotonic() > self.deadline or (
            self._shutdown_event and self._shutdown_event.is_set()
        ):
            raise SpeedtestUploadTimeout()

        remaining = self.length - self.total_bytes_read
        if remaining <= 0:
            return b""

        max_alloc = len(DUMMY_CHUNK)

        if n < 0 or n > remaining:
            read_size = min(remaining, max_alloc)
        else:
            read_size = min(n, remaining, max_alloc)

        chunk = DUMMY_CHUNK[:read_size]

        self.total_bytes_read += read_size
        return chunk

    def __len__(self) -> int:
        return self.length


def upload_worker(
    request: urllib.request.Request,
    payload_data: HTTPUploaderData,
    shutdown_event: threading.Event | None = None,
) -> int:
    """Worker function for POSTing a payload, returning total bytes uploaded."""

    remaining_time = payload_data.deadline - time.monotonic()

    if remaining_time <= 0 or (shutdown_event and shutdown_event.is_set()):
        return 0

    try:
        with urllib.request.urlopen(request, timeout=remaining_time) as response:
            response.read(UPLOAD_RESPONSE_TRUNCATION)

        return payload_data.total_bytes_read

    except (urllib.error.URLError, TimeoutError, OSError, SpeedtestUploadTimeout):
        return payload_data.total_bytes_read
