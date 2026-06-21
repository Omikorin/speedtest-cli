"""
Handles multi-threaded execution of download and upload tests.
"""

import math
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from speedtest.http.request import build_user_agent
from speedtest.http.workers import HTTPUploaderData, download_worker, upload_worker
from speedtest.utils.logger import logger

__all__ = ["run_download_test", "run_upload_test"]


def run_download_test(
    best_server_url: str,
    shutdown_event: threading.Event | None = None,
    threads: int | None = None,
) -> tuple[int, float]:
    """
    Execute a multi-threaded download speed test against the target server.
    Returns a tuple of (bytes_received, download_speed_bps).
    """

    if not best_server_url:
        return 0, 0.0

    base_url = best_server_url.rsplit("/", 1)[0]

    sizes = [350, 500, 750, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
    counts = 4
    test_length = 10.0  # seconds

    headers = {"User-Agent": build_user_agent(), "Cache-Control": "no-cache"}
    requests: list[urllib.request.Request] = []

    timestamp = int(time.time() * 1000)
    req_id = 0

    for size in sizes:
        for _ in range(counts):
            url = f"{base_url}/random{size}x{size}.jpg?x={timestamp}.{req_id}"
            requests.append(urllib.request.Request(url, headers=headers))
            req_id += 1

    bytes_received = 0
    start_time = time.monotonic()

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = [
            executor.submit(download_worker, req, start_time, test_length, shutdown_event)
            for req in requests
        ]

        for future in as_completed(futures):
            try:
                bytes_received += future.result()
            except Exception as e:
                logger.debug(f"Download thread failed: {e}")

            if shutdown_event and shutdown_event.is_set():
                break

    stop_time = time.monotonic()
    elapsed = max(stop_time - start_time, 0.001)

    download_speed_bps = (bytes_received / elapsed) * 8.0

    return bytes_received, download_speed_bps


def run_upload_test(
    best_server_url: str,
    shutdown_event: threading.Event | None = None,
    threads: int | None = None,
) -> tuple[int, float]:
    """
    Execute a multi-threaded upload speed test against the target server.
    Returns a tuple of (bytes_sent, upload_speed_bps).
    """

    if not best_server_url:
        return 0, 0.0

    tmp_sizes = [524288, 1048576, 7340032]  # 0.5MB, 1MB, 7MB
    request_count = 50
    tmp_upload_count = math.ceil(request_count / len(tmp_sizes))

    raw_sizes = [size for size in tmp_sizes for _ in range(tmp_upload_count)]
    sizes = raw_sizes[:request_count]

    requests: list[urllib.request.Request] = []
    payloads: list[HTTPUploaderData] = []

    test_length = 10.0  # seconds
    user_agent = build_user_agent()
    timestamp = int(time.time() * 1000)

    delim = "&" if "?" in best_server_url else "?"

    # Prepare requests and allocate payloads before starting the clock
    for i, size in enumerate(sizes):
        data = HTTPUploaderData(
            length=size,
            start_time=0.0,  # Dummy value; will be stamped right before execution
            timeout=test_length,
            shutdown_event=shutdown_event,
        )

        url = f"{best_server_url}{delim}x={timestamp}.{i}"

        headers = {
            "User-Agent": user_agent,
            "Content-Length": str(size),
            "Cache-Control": "no-cache",
        }

        req = urllib.request.Request(url, data=data, headers=headers)

        requests.append(req)
        payloads.append(data)

    bytes_sent = 0
    start_time = time.monotonic()

    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = []

        for req, payload in zip(requests, payloads):
            # Stamp the real start time immediately before thread submission
            payload.start_time = start_time

            futures.append(executor.submit(upload_worker, req, payload, shutdown_event))

        for future in as_completed(futures):
            try:
                bytes_sent += future.result()
            except Exception as e:
                logger.debug(f"Upload thread failed: {e}")

            if shutdown_event and shutdown_event.is_set():
                break

    stop_time = time.monotonic()
    elapsed = max(stop_time - start_time, 0.001)

    upload_speed_bps = (bytes_sent / elapsed) * 8.0

    return bytes_sent, upload_speed_bps
