"""
Handles multi-threaded execution of download and upload tests.
"""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.request import OpenerDirector, Request

from speedtest.http.request import build_request
from speedtest.http.workers import HTTPUploaderData, download_worker, upload_worker
from speedtest.utils.logger import logger

__all__ = ["run_download_test", "run_upload_test"]


def run_download_test(
    best_server_url: str,
    config: dict[str, Any],
    opener: OpenerDirector | None,
    shutdown_event: threading.Event | None,
    threads: int | None = None,
) -> tuple[int, float]:
    """
    Execute a multi-threaded download speed test against the target server.
    Returns a tuple of (bytes_received, download_speed_bps).
    """

    urls: list[str] = []

    base_url = os.path.dirname(best_server_url)

    sizes = config.get("sizes", {}).get("download", [])
    counts = config.get("counts", {}).get("download", 4)

    for size in sizes:
        for _ in range(counts):
            urls.append(f"{base_url}/random{size}x{size}.jpg")

    requests = [build_request(url, bump=str(i)) for i, url in enumerate(urls)]
    max_threads = threads or config.get("threads", {}).get("download", 4)

    bytes_received = 0
    start = time.monotonic()

    test_length = config.get("length", {}).get("download", 10)

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [
            executor.submit(
                download_worker,
                req,
                start,
                test_length,
                opener=opener,
                shutdown_event=shutdown_event,
            )
            for req in requests
        ]

        for future in as_completed(futures):
            try:
                bytes_received += future.result()
            except Exception as e:
                logger.debug(f"Download thread failed: {e}")

    stop = time.monotonic()

    elapsed = max(stop - start, 0.001)
    download_speed = (bytes_received / elapsed) * 8.0

    # Legacy behavior: Adapt upload thread count dynamically based on download performance
    if download_speed > 100000 and "threads" in config:
        config["threads"]["upload"] = 8

    return bytes_received, download_speed


def run_upload_test(
    best_server_url: str,
    config: dict[str, Any],
    opener: OpenerDirector | None,
    shutdown_event: threading.Event | None,
    threads: int | None = None,
) -> tuple[int, float]:
    """
    Execute a multi-threaded upload speed test against the target server.
    Returns a tuple of (bytes_sent, upload_speed_bps).
    """

    raw_sizes = [
        size
        for size in config.get("sizes", {}).get("upload", [])
        for _ in range(config.get("counts", {}).get("upload", 1))
    ]

    # Truncate to the exact maximum needed BEFORE looping to save RAM overhead
    request_count = config.get("upload_max", len(raw_sizes))
    sizes = raw_sizes[:request_count]

    requests: list[Request] = []
    payloads: list[HTTPUploaderData] = []

    test_length = config.get("length", {}).get("upload", 10)

    # Prepare requests and allocate payloads before starting the clock
    for size in sizes:
        data = HTTPUploaderData(
            length=size,
            start_time=0.0,  # Dummy value; will be updated right before execution
            timeout=test_length,
            shutdown_event=shutdown_event,
        )

        headers = {"Content-length": str(size)}
        req = build_request(best_server_url, data, headers=headers)

        requests.append(req)
        payloads.append(data)

    max_threads = threads or config.get("threads", {}).get("upload", 4)
    bytes_sent = 0

    start = time.monotonic()

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = []

        for req, payload in zip(requests, payloads):
            # Stamp the real start time immediately before submission
            payload.start_time = start

            futures.append(
                executor.submit(
                    upload_worker,
                    req,
                    payload,
                    test_length,
                    opener=opener,
                    shutdown_event=shutdown_event,
                )
            )

        for future in as_completed(futures):
            try:
                bytes_sent += future.result()
            except Exception as e:
                logger.debug(f"Upload thread failed: {e}")

    stop = time.monotonic()

    elapsed = max(stop - start, 0.001)
    upload_speed = (bytes_sent / elapsed) * 8.0

    return bytes_sent, upload_speed
