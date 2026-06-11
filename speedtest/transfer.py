import os
import threading
import time
import timeit
from queue import Queue
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
    in_flight = {"threads": 0}

    def producer(q: Queue, reqs: List[Any], req_count: int) -> None:
        for i, request in enumerate(reqs):
            thread = HTTPDownloader(
                i,
                request,
                start,
                config["length"]["download"],
                opener=opener,
                shutdown_event=shutdown_event,
            )
            while in_flight["threads"] >= max_threads:
                time.sleep(0.001)

            thread.start()
            q.put(thread, True)
            in_flight["threads"] += 1
            callback(i, req_count, start=True)

    finished: List[float] = []

    def consumer(q: Queue, req_count: int) -> None:
        while len(finished) < req_count:
            thread = q.get(True)
            while thread.is_alive():
                thread.join(timeout=0.001)

            in_flight["threads"] -= 1
            finished.append(sum(thread.result))
            callback(thread.i, req_count, end=True)

    q: Queue = Queue(max_threads)
    prod_thread = threading.Thread(target=producer, args=(q, requests, request_count))
    cons_thread = threading.Thread(target=consumer, args=(q, request_count))

    start = timeit.default_timer()
    prod_thread.start()
    cons_thread.start()

    while prod_thread.is_alive():
        prod_thread.join(timeout=0.001)
    while cons_thread.is_alive():
        cons_thread.join(timeout=0.001)

    stop = timeit.default_timer()

    bytes_received = sum(finished)
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
    in_flight = {"threads": 0}

    def producer(q: Queue, reqs: List[Tuple[Any, int]], req_count: int) -> None:
        for i, request in enumerate(reqs[:req_count]):
            thread = HTTPUploader(
                i,
                request[0],
                start,
                request[1],
                config["length"]["upload"],
                opener=opener,
                shutdown_event=shutdown_event,
            )
            while in_flight["threads"] >= max_threads:
                time.sleep(0.001)

            thread.start()
            q.put(thread, True)
            in_flight["threads"] += 1
            callback(i, req_count, start=True)

    finished: List[float] = []

    def consumer(q: Queue, req_count: int) -> None:
        while len(finished) < req_count:
            thread = q.get(True)
            while thread.is_alive():
                thread.join(timeout=0.001)

            in_flight["threads"] -= 1
            finished.append(thread.result)
            callback(thread.i, req_count, end=True)

    q: Queue = Queue(max_threads)
    prod_thread = threading.Thread(target=producer, args=(q, requests, request_count))
    cons_thread = threading.Thread(target=consumer, args=(q, request_count))

    start = timeit.default_timer()
    prod_thread.start()
    cons_thread.start()

    while prod_thread.is_alive():
        prod_thread.join(timeout=0.1)
    while cons_thread.is_alive():
        cons_thread.join(timeout=0.1)

    stop = timeit.default_timer()

    bytes_sent = sum(finished)
    upload_speed = (bytes_sent / (stop - start)) * 8.0

    return bytes_sent, upload_speed
