import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.request import OpenerDirector, Request

from speedtest.http import (
    HTTPUploaderData,
    build_request,
    download_worker,
    upload_worker,
)

__all__ = ["run_download_test", "run_upload_test"]


def run_download_test(
    best_server_url: str,
    config: dict[str, Any],
    opener: OpenerDirector | None,
    shutdown_event: threading.Event | None,
    threads: int | None = None,
) -> tuple[float, float]:
    """
    Execute a multi-threaded download speed test against the target server.
    Returns a tuple of (bytes_received, download_speed_bps).
    """

    urls: list[str] = []
    base_url = os.path.dirname(best_server_url)

    for size in config["sizes"]["download"]:
        for _ in range(config["counts"]["download"]):
            urls.append(f"{base_url}/random{size}x{size}.jpg")

    requests = [build_request(url, bump=str(i)) for i, url in enumerate(urls)]
    max_threads = threads or config["threads"]["download"]

    bytes_received = 0.0
    start = time.monotonic()

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [
            executor.submit(
                download_worker,
                req,
                start,
                config["length"]["download"],
                opener=opener,
                shutdown_event=shutdown_event,
            )
            for req in requests
        ]

        for future in as_completed(futures):
            bytes_received += future.result()

    stop = time.monotonic()
    download_speed = (bytes_received / (stop - start)) * 8.0

    # Adapt upload thread count dynamically based on download performance
    if download_speed > 100000:
        config["threads"]["upload"] = 8

    return bytes_received, download_speed


def run_upload_test(
    best_server_url: str,
    config: dict[str, Any],
    opener: OpenerDirector | None,
    shutdown_event: threading.Event | None,
    pre_allocate: bool = True,
    threads: int | None = None,
) -> tuple[float, float]:
    """
    Execute a multi-threaded upload speed test against the target server.
    Returns a tuple of (bytes_sent, upload_speed_bps).
    """

    sizes = [
        size
        for size in config["sizes"]["upload"]
        for _ in range(config["counts"]["upload"])
    ]

    request_count = config["upload_max"]
    requests: list[Request] = []
    payloads: list[HTTPUploaderData] = []

    # Prepare requests and allocate payloads before starting the clock
    for size in sizes:
        data = HTTPUploaderData(
            length=size,
            start_time=0.0,  # Dummy value; will be updated right before execution
            timeout=config["length"]["upload"],
            shutdown_event=shutdown_event,
        )
        if pre_allocate:
            data.pre_allocate()

        headers = {"Content-length": str(size)}

        req = build_request(best_server_url, data, headers=headers)

        requests.append(req)
        payloads.append(data)

    max_threads = threads or config["threads"]["upload"]
    bytes_sent = 0.0

    start = time.monotonic()

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = []

        for req, payload in zip(requests[:request_count], payloads[:request_count]):
            # Stamp the real start time immediately before submission
            payload.start_time = start

            futures.append(
                executor.submit(
                    upload_worker,
                    req,
                    payload,
                    config["length"]["upload"],
                    opener=opener,
                    shutdown_event=shutdown_event,
                )
            )

        for future in as_completed(futures):
            bytes_sent += future.result()

    stop = time.monotonic()
    upload_speed = (bytes_sent / (stop - start)) * 8.0

    return bytes_sent, upload_speed
