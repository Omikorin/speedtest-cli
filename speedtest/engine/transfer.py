"""
Handles multi-threaded execution of download and upload tests.
"""

import math
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import OpenerDirector, Request

from speedtest.http.request import build_request
from speedtest.http.workers import HTTPUploaderData, download_worker, upload_worker
from speedtest.utils.logger import logger

__all__ = ["run_download_test", "run_upload_test"]


def run_download_test(
    best_server_url: str,
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

    # config.sizes.download
    sizes = [350, 500, 750, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
    counts = 4  # config.counts.download

    for size in sizes:
        for _ in range(counts):
            urls.append(f"{base_url}/random{size}x{size}.jpg")

    requests = [build_request(url, bump=str(i)) for i, url in enumerate(urls)]
    max_threads = threads

    bytes_received = 0
    start = time.monotonic()

    test_length = 10  # config.length.download

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

    return bytes_received, download_speed


def run_upload_test(
    best_server_url: str,
    opener: OpenerDirector | None,
    shutdown_event: threading.Event | None,
    threads: int | None = None,
) -> tuple[int, float]:
    """
    Execute a multi-threaded upload speed test against the target server.
    Returns a tuple of (bytes_sent, upload_speed_bps).
    """

    tmp_upload_max = 50  # maxchunkcount, same situation
    tmp_sizes = [524288, 1048576, 7340032]
    tmp_size_count = len(tmp_sizes)
    tmp_upload_count = math.ceil(tmp_upload_max / tmp_size_count)

    raw_sizes = [size for size in tmp_sizes for _ in range(tmp_upload_count)]

    # Truncate to the exact maximum needed BEFORE looping to save RAM overhead
    request_count = 50  # maxchunkcount
    sizes = raw_sizes[:request_count]

    requests: list[Request] = []
    payloads: list[HTTPUploaderData] = []

    test_length = 10  # config.length.upload

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

    max_threads = threads
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
