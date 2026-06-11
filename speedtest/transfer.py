import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

from speedtest.http import HTTPDownloader, HTTPUploader, HTTPUploaderData, build_request
from speedtest.utils import do_nothing

__all__ = ["run_download_test", "run_upload_test"]


def run_download_test(
    best_server_url: str,
    config: Dict[str, Any],
    opener: Any,
    secure: bool,
    shutdown_event: Any,
    callback: Callable = do_nothing,
    threads: Optional[int] = None,
) -> Tuple[float, float]:
    """
    Execute multi-threaded download speed test against the target server.
    Returns a tuple of (bytes_received, download_speed_bps).
    """

    urls = []
    base_url = os.path.dirname(best_server_url)

    for size in config["sizes"]["download"]:
        for _ in range(config["counts"]["download"]):
            urls.append(f"{base_url}/random{size}x{size}.jpg")

    request_count = len(urls)
    requests = [build_request(url, bump=i, secure=secure) for i, url in enumerate(urls)]
    max_threads = threads or config["threads"]["download"]

    # wrapper to execute the legacy thread payload
    # TODO: modernize this
    def _download_task(i: int, request: Any, start_time: float) -> float:
        callback(i, request_count, start=True)
        task = HTTPDownloader(
            i,
            request,
            start_time,
            config["length"]["download"],
            opener=opener,
            shutdown_event=shutdown_event,
        )
        task.run()
        callback(i, request_count, end=True)
        return sum(task.result)

    bytes_received = 0.0
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [
            executor.submit(_download_task, i, req, start)
            for i, req in enumerate(requests)
        ]

        for future in as_completed(futures):
            bytes_received += future.result()

    stop = time.perf_counter()
    download_speed = (bytes_received / (stop - start)) * 8.0

    # adapt upload thread count dynamically based on download performance
    if download_speed > 100000:
        config["threads"]["upload"] = 8

    return bytes_received, download_speed


def run_upload_test(
    best_server_url: str,
    config: Dict[str, Any],
    opener: Any,
    secure: bool,
    shutdown_event: Any,
    callback: Callable = do_nothing,
    pre_allocate: bool = True,
    threads: Optional[int] = None,
) -> Tuple[float, float]:
    """
    Execute multi-threaded upload speed test against the target server.
    Returns a tuple of (bytes_sent, upload_speed_bps).
    """

    sizes = [
        size
        for size in config["sizes"]["upload"]
        for _ in range(config["counts"]["upload"])
    ]

    request_count = config["upload_max"]
    requests = []

    for i, size in enumerate(sizes):
        data = HTTPUploaderData(
            size,
            0,
            config["length"]["upload"],
            shutdown_event=shutdown_event,
        )
        if pre_allocate:
            data.pre_allocate()

        headers = {"Content-length": str(size)}
        req = build_request(best_server_url, data, secure=secure, headers=headers)
        requests.append((req, size))

    max_threads = threads or config["threads"]["upload"]

    # wrapper to execute the legacy thread payload
    # TODO: modernize this
    def _upload_task(i: int, request: Any, size: int, start_time: float) -> float:
        callback(i, request_count, start=True)
        task = HTTPUploader(
            i,
            request,
            start_time,
            size,
            config["length"]["upload"],
            opener=opener,
            shutdown_event=shutdown_event,
        )
        task.run()
        callback(i, request_count, end=True)
        return task.result

    bytes_sent = 0.0
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        # old code explicitly sliced requests to req_count
        futures = [
            executor.submit(_upload_task, i, req, size, start)
            for i, (req, size) in enumerate(requests[:request_count])
        ]

        for future in as_completed(futures):
            bytes_sent += future.result()

    stop = time.perf_counter()
    upload_speed = (bytes_sent / (stop - start)) * 8.0

    return bytes_sent, upload_speed
