"""
Tests for the multi-threaded download and upload orchestration.
"""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import httpx2
import pytest
from speedtest.api.transfer import (
    _generate_download_requests,
    _generate_upload_payloads,
    _resolve_upload_url,
    run_download_test,
    run_upload_test,
)

Handler = Callable[[httpx2.Request], httpx2.Response]

UPLOAD_TOTAL_BYTES = 17 * 524288 + 17 * 1048576 + 16 * 7340032


@pytest.fixture
def mock_http(monkeypatch: pytest.MonkeyPatch) -> Callable[[Handler], None]:
    """Route every httpx2.Client created by the code under test through a MockTransport."""

    real_client = httpx2.Client

    def install(handler: Handler) -> None:
        transport = httpx2.MockTransport(handler)
        monkeypatch.setattr(httpx2, "Client", lambda **kwargs: real_client(transport=transport, **kwargs))

    return install


# --- request generators ---


def test_download_requests_cover_every_size_four_times() -> None:
    requests = list(_generate_download_requests("http://host.example/speedtest/upload.php"))

    assert len(requests) == 40
    paths = [r.url.path for r in requests]
    assert paths[:4] == ["/speedtest/random350x350.jpg"] * 4
    assert paths[-4:] == ["/speedtest/random4000x4000.jpg"] * 4
    assert all(r.method == "GET" for r in requests)
    assert all(r.headers["Cache-Control"] == "no-cache" for r in requests)


def test_download_requests_have_unique_cache_busting_urls() -> None:
    requests = list(_generate_download_requests("http://host.example/speedtest/upload.php"))

    assert len({str(r.url) for r in requests}) == len(requests)


def test_upload_payloads_match_declared_sizes_and_headers() -> None:
    event = threading.Event()

    tasks = list(_generate_upload_payloads("http://host.example/upload.php", 10.0, event))

    assert len(tasks) == 50
    assert sum(p.length for _, p in tasks) == UPLOAD_TOTAL_BYTES
    for request, payload in tasks:
        assert request.method == "POST"
        assert request.headers["Content-Length"] == str(payload.length)
        assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert payload.timeout == pytest.approx(10.0)


def test_upload_payloads_have_unique_urls() -> None:
    tasks = list(_generate_upload_payloads("http://host.example/upload.php", 10.0, None))

    assert len({str(r.url) for r, _ in tasks}) == 50
    assert all("x" in parse_qs(urlparse(str(r.url)).query) for r, _ in tasks)


def test_upload_payloads_append_to_existing_query_string() -> None:
    tasks = list(_generate_upload_payloads("http://host.example/upload.php?token=abc", 10.0, None))

    query = parse_qs(urlparse(str(tasks[0][0].url)).query)
    assert query["token"] == ["abc"]
    assert "x" in query


# --- _resolve_upload_url ---


def test_resolve_upload_url_follows_redirects(mock_http: Callable[[Handler], None]) -> None:
    final = "https://server-1.example.net:8080/speedtest/upload.php"

    def handler(request: httpx2.Request) -> httpx2.Response:
        if str(request.url) == final:
            return httpx2.Response(200)
        return httpx2.Response(307, headers={"Location": final})

    mock_http(handler)

    assert _resolve_upload_url("http://host.example/speedtest/upload.php") == final


def test_resolve_upload_url_falls_back_on_network_error(mock_http: Callable[[Handler], None]) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused", request=request)

    mock_http(handler)

    assert _resolve_upload_url("http://host.example/upload.php") == "http://host.example/upload.php"


# --- run_download_test ---


def test_run_download_test_without_url_does_nothing() -> None:
    assert run_download_test("") == (0, 0.0)


@pytest.mark.parametrize("runner", [run_download_test, run_upload_test])
@pytest.mark.parametrize("threads", [0, -1])
def test_transfer_rejects_non_positive_thread_count(runner: Callable[..., object], threads: int) -> None:
    with pytest.raises(ValueError, match="threads must be at least 1"):
        runner("http://host.example/upload.php", threads=threads)


def test_run_download_test_sums_all_responses(mock_http: Callable[[Handler], None]) -> None:
    mock_http(lambda _: httpx2.Response(200, content=b"x" * 1000))

    received, bps = run_download_test("http://host.example/speedtest/upload.php")

    assert received == 40 * 1000
    assert bps > 0


def test_run_download_test_survives_failing_workers() -> None:
    def worker(_client: object, request: httpx2.Request, *_: object) -> int:
        if "random350x350" in str(request.url):
            raise OSError("socket closed")
        return 100

    with patch("speedtest.api.transfer.download_worker", side_effect=worker):
        received, _ = run_download_test("http://host.example/speedtest/upload.php")

    assert received == 36 * 100  # 4 of the 40 requests failed


def test_run_download_test_stops_collecting_on_shutdown() -> None:
    event = threading.Event()

    def worker(*_: object) -> int:
        event.set()
        return 100

    with patch("speedtest.api.transfer.download_worker", side_effect=worker):
        received, _ = run_download_test("http://host.example/speedtest/upload.php", shutdown_event=event)

    assert received == 100  # only the first completed future was counted


def test_run_download_test_honours_thread_count() -> None:
    with patch("speedtest.api.transfer.ThreadPoolExecutor", wraps=ThreadPoolExecutor) as executor:
        run_download_test("http://host.example/speedtest/upload.php", threads=3)

    assert executor.call_args.kwargs["max_workers"] == 3


# --- run_upload_test ---


def test_run_upload_test_without_url_does_nothing() -> None:
    assert run_upload_test("") == (0, 0.0)


def test_run_upload_test_sends_every_byte_to_resolved_url(mock_http: Callable[[Handler], None]) -> None:
    final = "https://server-1.example.net:8080/speedtest/upload.php"
    hosts: set[str] = set()

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.host == "host.example":
            return httpx2.Response(307, headers={"Location": final})
        hosts.add(request.url.host)
        request.read()
        return httpx2.Response(200)

    mock_http(handler)

    sent, bps = run_upload_test("http://host.example/speedtest/upload.php")

    assert sent == UPLOAD_TOTAL_BYTES
    assert bps > 0
    assert hosts == {"server-1.example.net"}


def test_run_upload_test_survives_failing_workers() -> None:
    calls = 0
    lock = threading.Lock()

    def worker(*_: object) -> int:
        nonlocal calls
        with lock:
            calls += 1
            first = calls == 1
        if first:
            raise OSError("socket closed")
        return 10

    with (
        patch("speedtest.api.transfer._resolve_upload_url", side_effect=lambda url: url),
        patch("speedtest.api.transfer.upload_worker", side_effect=worker),
    ):
        sent, _ = run_upload_test("http://host.example/upload.php")

    assert sent == 49 * 10


def test_run_upload_test_stops_collecting_on_shutdown() -> None:
    event = threading.Event()

    def worker(*_: object) -> int:
        event.set()
        return 10

    with (
        patch("speedtest.api.transfer._resolve_upload_url", side_effect=lambda url: url),
        patch("speedtest.api.transfer.upload_worker", side_effect=worker),
    ):
        sent, _ = run_upload_test("http://host.example/upload.php", shutdown_event=event)

    assert sent == 10


def test_run_upload_test_stamps_start_time_before_dispatch() -> None:
    seen: list[float] = []

    def worker(_client: object, _request: object, payload: MagicMock, *_: object) -> int:
        seen.append(payload.start_time)
        return 0

    with (
        patch("speedtest.api.transfer._resolve_upload_url", side_effect=lambda url: url),
        patch("speedtest.api.transfer.upload_worker", side_effect=worker),
    ):
        run_upload_test("http://host.example/upload.php")

    assert len(seen) == 50
    assert all(start > 0.0 for start in seen)  # generator's dummy 0.0 was replaced
