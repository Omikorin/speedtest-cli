"""
Handles multi-threaded execution of download and upload tests.
"""

import math
import threading
import time
import urllib.request
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed

from speedtest.engine.network import (
    HTTPUploaderData,
    build_user_agent,
    download_worker,
    upload_worker,
)
from speedtest.models.context import RunContext
from speedtest.utils.logger import logger

__all__ = ["run_download_test", "run_upload_test"]


def _generate_download_requests(best_server_url: str) -> Iterator[urllib.request.Request]:
    """Pure generator yielding Request objects for the download test."""

    base_url = best_server_url.rsplit("/", 1)[0]
    sizes = [350, 500, 750, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
    counts = 4
    headers = {"User-Agent": build_user_agent(), "Cache-Control": "no-cache"}
    timestamp = int(time.time() * 1000)
    req_id = 0

    for size in sizes:
        for _ in range(counts):
            url = f"{base_url}/random{size}x{size}.jpg?x={timestamp}.{req_id}"
            yield urllib.request.Request(url, headers=headers)
            req_id += 1


def _generate_upload_payloads(
    best_server_url: str, test_length: float, shutdown_event: threading.Event | None
) -> Iterator[tuple[urllib.request.Request, HTTPUploaderData]]:
    """Pure generator yielding Request and Payload tuples for the upload test."""

    tmp_sizes = [524288, 1048576, 7340032]  # 0.5MB, 1MB, 7MB
    request_count = 50
    tmp_upload_count = math.ceil(request_count / len(tmp_sizes))

    raw_sizes = [size for size in tmp_sizes for _ in range(tmp_upload_count)]
    sizes = raw_sizes[:request_count]

    user_agent = build_user_agent()
    timestamp = int(time.time() * 1000)
    delim = "&" if "?" in best_server_url else "?"

    for i, size in enumerate(sizes):
        data = HTTPUploaderData(
            length=size,
            start_time=0.0,
            timeout=test_length,
            shutdown_event=shutdown_event,
        )
        url = f"{best_server_url}{delim}x={timestamp}.{i}"
        headers = {
            "User-Agent": user_agent,
            "Content-Length": str(size),
            "Cache-Control": "no-cache",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        yield req, data


def run_download_test(best_server_url: str, ctx: RunContext) -> tuple[int, float]:
    """
    Execute a multi-threaded download speed test against the target server.
    Returns a tuple of (bytes_received, download_speed_bps).
    """

    if not best_server_url:
        return 0, 0.0

    test_length = 10.0
    bytes_received = 0
    start_time = time.monotonic()

    requests = list(_generate_download_requests(best_server_url))

    with ThreadPoolExecutor(max_workers=ctx.threads) as executor:
        futures = [
            executor.submit(download_worker, req, start_time, test_length, ctx.shutdown_event)
            for req in requests
        ]

        for future in as_completed(futures):
            try:
                bytes_received += future.result()
            except Exception as e:
                logger.debug(f"Download thread failed: {e}")

            if ctx.shutdown_event and ctx.shutdown_event.is_set():
                break

    elapsed = max(time.monotonic() - start_time, 0.001)
    return bytes_received, (bytes_received / elapsed) * 8.0


def run_upload_test(best_server_url: str, ctx: RunContext) -> tuple[int, float]:
    """
    Execute a multi-threaded upload speed test against the target server.
    Returns a tuple of (bytes_sent, upload_speed_bps).
    """

    if not best_server_url:
        return 0, 0.0

    test_length = 10.0
    bytes_sent = 0

    tasks = list(_generate_upload_payloads(best_server_url, test_length, ctx.shutdown_event))
    start_time = time.monotonic()

    with ThreadPoolExecutor(max_workers=ctx.threads) as executor:
        futures = []
        for req, payload in tasks:
            payload.start_time = start_time
            futures.append(executor.submit(upload_worker, req, payload, ctx.shutdown_event))

        for future in as_completed(futures):
            try:
                bytes_sent += future.result()
            except Exception as e:
                logger.debug(f"Upload thread failed: {e}")

            if ctx.shutdown_event and ctx.shutdown_event.is_set():
                break

    elapsed = max(time.monotonic() - start_time, 0.001)
    return bytes_sent, (bytes_sent / elapsed) * 8.0
