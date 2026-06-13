"""
Threadpool worker functions and payload data classes
"""

import threading
import time
from io import BytesIO
from urllib.request import OpenerDirector, Request, urlopen

from speedtest.exceptions import SpeedtestCLIError, SpeedtestUploadTimeout
from speedtest.http.errors import HTTP_ERRORS, UPLOAD_ERRORS

__all__ = [
    "download_worker",
    "HTTPUploaderData",
    "upload_worker",
]

# --- Constants ---
CHUNK_SIZE_BYTES = 10240
PAYLOAD_MULTIPLIER = 36.0
UPLOAD_RESPONSE_TRUNCATION = 11


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

    try:
        if (time.monotonic() - start_time) <= timeout:
            with _opener(request) as response:
                while (
                    not _shutdown_event.is_set()
                    and (time.monotonic() - start_time) <= timeout
                ):
                    chunk = response.read(CHUNK_SIZE_BYTES)
                    if not chunk:
                        break

                    total_downloaded += len(chunk)
    except HTTP_ERRORS:
        pass

    return total_downloaded


class HTTPUploaderData:
    """File-like object to cleanly truncate the upload once the timeout is reached."""

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
        self._data: BytesIO | None = None
        self.total_bytes_read = 0

    def pre_allocate(self) -> None:
        chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        multiplier = int(round(self.length / PAYLOAD_MULTIPLIER))

        try:
            payload = f"content1={(chars * multiplier)[: self.length - 9]}".encode()
            self._data = BytesIO(payload)
        except MemoryError:
            raise SpeedtestCLIError(
                "Insufficient memory to pre-allocate upload data. Please use --no-pre-allocate"
            )

    @property
    def data(self) -> BytesIO:
        if not self._data:
            self.pre_allocate()
        return self._data

    def read(self, n: int = CHUNK_SIZE_BYTES) -> bytes:
        if (
            time.monotonic() - self.start_time
        ) <= self.timeout and not self._shutdown_event.is_set():
            chunk = self.data.read(n)
            self.total_bytes_read += len(chunk)
            return chunk

        raise SpeedtestUploadTimeout()

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

    try:
        if (
            time.monotonic() - payload_data.start_time
        ) <= timeout and not _shutdown_event.is_set():
            with _opener(request) as response:
                response.read(UPLOAD_RESPONSE_TRUNCATION)
            return payload_data.total_bytes_read
        return 0
    except UPLOAD_ERRORS:
        # Fallback to the amount of bytes we successfully managed to upload before crash/timeout
        return payload_data.total_bytes_read
