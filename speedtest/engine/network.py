# speedtest/engine/network.py

"""
Low-level network utilities, HTTP workers, and payload generation.
"""

import platform
import socket
import threading
import time
from collections.abc import Iterator
from functools import cache

import httpx2

from speedtest import __version__
from speedtest.exceptions import UploadTimeoutError
from speedtest.utils.logger import logger

# --- Constants ---
CHUNK_SIZE_BYTES = 10240
UPLOAD_RESPONSE_TRUNCATION = 11
DUMMY_CHUNK = b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ" * 300

__all__ = [
    "HTTPUploaderData",
    "build_user_agent",
    "download_worker",
    "measure_tcp_latency",
    "upload_worker",
]


@cache
def build_user_agent() -> str:
    """Build and cache a User-Agent string."""

    system = platform.system() or "UnknownOS"
    machine = platform.machine() or "UnknownArch"

    user_agent = f"Mozilla/5.0 ({system}; {machine}) Python/{platform.python_version()} speedtest-cli/{__version__}"

    logger.debug(f"User-Agent: {user_agent}")
    return user_agent


def measure_tcp_latency(ip: str, port: int, timeout: float = 5.0) -> float:
    """
    Measures pure TCP connection latency to a resolved IP.
    Returns latency in milliseconds, or 3600000.0 (1 hour penalty) on failure.
    """

    start_time = time.monotonic()

    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return (time.monotonic() - start_time) * 1000.0
    except TimeoutError, OSError:
        return 3600000.0


class HTTPUploaderData:
    """
    Iterable object to stream dummy data for uploads with O(1) memory footprint.
    """

    def __init__(
        self,
        length: int,
        start_time: float,
        timeout: float,
        shutdown_event: threading.Event | None = None,
    ) -> None:
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

        if time.monotonic() > self.deadline or (self._shutdown_event and self._shutdown_event.is_set()):
            raise UploadTimeoutError()

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

    def __iter__(self) -> Iterator[bytes]:
        """Provides native httpx2 compatibility for streaming generator payloads."""

        while chunk := self.read(CHUNK_SIZE_BYTES):
            yield chunk

    def __len__(self) -> int:
        return self.length


def download_worker(
    client: httpx2.Client,
    request: httpx2.Request,
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
        response = client.send(request, stream=True)

        try:
            for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE_BYTES):
                if time.monotonic() > deadline or (shutdown_event and shutdown_event.is_set()):
                    break
                total_downloaded += len(chunk)
        finally:
            response.close()

    except httpx2.RequestError:
        # Silently absorb network drops during high-concurrency stress testing
        pass

    return total_downloaded


def upload_worker(
    client: httpx2.Client,
    request: httpx2.Request,
    payload_data: HTTPUploaderData,
    shutdown_event: threading.Event | None = None,
) -> int:
    """Worker function for POSTing a payload, returning total bytes uploaded."""

    remaining_time = payload_data.deadline - time.monotonic()

    if remaining_time <= 0 or (shutdown_event and shutdown_event.is_set()):
        return 0

    try:
        client.send(request)
        return payload_data.total_bytes_read

    except httpx2.RequestError, UploadTimeoutError:
        return payload_data.total_bytes_read
