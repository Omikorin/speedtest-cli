"""
Tests for low-level network helpers and HTTP workers.

Workers run against a real httpx2.Client backed by MockTransport, so request
handling, streaming, and error mapping are exercised for real.
"""

import threading
import time
from collections.abc import Callable, Iterator
from unittest.mock import MagicMock, patch

import httpx2
import pytest
from speedtest import __version__
from speedtest.engine.network import (
    CHUNK_SIZE_BYTES,
    UPLOAD_BODY_PREFIX,
    HTTPUploaderData,
    build_user_agent,
    download_worker,
    measure_tcp_latency,
    upload_worker,
)
from speedtest.exceptions import UploadTimeoutError

PENALTY_MS = 3600000.0

Handler = Callable[[httpx2.Request], httpx2.Response]


def _client(handler: Handler) -> httpx2.Client:
    return httpx2.Client(transport=httpx2.MockTransport(handler))


def _payload(length: int, *, timeout: float = 60.0, event: threading.Event | None = None) -> HTTPUploaderData:
    return HTTPUploaderData(length=length, start_time=time.monotonic(), timeout=timeout, shutdown_event=event)


def _upload_request(payload: HTTPUploaderData) -> httpx2.Request:
    return httpx2.Request(
        "POST", "http://example.com/upload.php", headers={"Content-Length": str(payload.length)}, content=payload
    )


# --- build_user_agent ---


def test_build_user_agent_identifies_the_tool() -> None:
    user_agent = build_user_agent()

    assert user_agent.startswith("Mozilla/5.0 (")
    assert f"speedtest-cli/{__version__}" in user_agent
    assert build_user_agent() is user_agent  # cached


# --- measure_tcp_latency ---


@patch("speedtest.engine.network.socket.create_connection")
def test_measure_tcp_latency_returns_elapsed_milliseconds(mock_connect: MagicMock) -> None:
    latency = measure_tcp_latency("10.0.0.1", 80, timeout=2.0)

    mock_connect.assert_called_once_with(("10.0.0.1", 80), timeout=2.0)
    assert 0.0 <= latency < PENALTY_MS


@pytest.mark.parametrize("error", [TimeoutError(), ConnectionRefusedError()])
@patch("speedtest.engine.network.socket.create_connection")
def test_measure_tcp_latency_failure_is_penalised(mock_connect: MagicMock, error: OSError) -> None:
    mock_connect.side_effect = error

    assert measure_tcp_latency("10.0.0.1", 80) == PENALTY_MS


# --- HTTPUploaderData ---


def test_uploader_deadline_follows_start_time() -> None:
    data = HTTPUploaderData(length=10, start_time=100.0, timeout=10.0)
    assert data.deadline == pytest.approx(110.0)

    data.start_time = 200.0
    assert data.deadline == pytest.approx(210.0)


def test_uploader_len_is_declared_length() -> None:
    assert len(_payload(12345)) == 12345


def test_uploader_stream_has_exact_length_and_form_prefix() -> None:
    length = CHUNK_SIZE_BYTES * 2 + 123
    data = _payload(length)

    body = b"".join(data)

    assert len(body) == length
    assert body.startswith(UPLOAD_BODY_PREFIX)
    assert data.total_bytes_read == length


def test_uploader_prefix_only_on_first_chunk() -> None:
    data = _payload(CHUNK_SIZE_BYTES * 2)

    first, second = list(data)

    assert first.startswith(UPLOAD_BODY_PREFIX)
    assert not second.startswith(UPLOAD_BODY_PREFIX)


def test_uploader_tiny_payload_is_sent_without_prefix() -> None:
    data = _payload(len(UPLOAD_BODY_PREFIX))

    assert data.read() == b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"[: len(UPLOAD_BODY_PREFIX)]


def test_uploader_read_respects_requested_size() -> None:
    data = _payload(1000)

    assert len(data.read(100)) == 100
    assert data.total_bytes_read == 100


def test_uploader_read_is_capped_by_remaining_and_chunk_size() -> None:
    data = _payload(CHUNK_SIZE_BYTES + 10)

    assert len(data.read(10**9)) == CHUNK_SIZE_BYTES
    assert len(data.read(10**9)) == 10


def test_uploader_read_returns_empty_when_exhausted() -> None:
    data = _payload(10)
    data.read()

    assert data.read() == b""


def test_uploader_raises_after_deadline() -> None:
    data = HTTPUploaderData(length=100, start_time=time.monotonic() - 5, timeout=1.0)

    with pytest.raises(UploadTimeoutError):
        data.read()


def test_uploader_raises_when_shutdown_requested() -> None:
    event = threading.Event()
    data = _payload(100, event=event)
    event.set()

    with pytest.raises(UploadTimeoutError):
        data.read()


# --- download_worker ---


def test_download_worker_counts_all_bytes() -> None:
    with _client(lambda _: httpx2.Response(200, content=b"x" * 100_000)) as client:
        total = download_worker(client, httpx2.Request("GET", "http://example.com/a"), time.monotonic(), 10.0)

    assert total == 100_000


def test_download_worker_skips_when_deadline_already_passed() -> None:
    handler = MagicMock()

    with _client(handler) as client:
        total = download_worker(client, httpx2.Request("GET", "http://example.com/a"), time.monotonic() - 100, 10.0)

    assert total == 0
    handler.assert_not_called()


def test_download_worker_skips_when_shutdown_already_requested() -> None:
    event = threading.Event()
    event.set()
    handler = MagicMock()

    with _client(handler) as client:
        total = download_worker(client, httpx2.Request("GET", "http://example.com/a"), time.monotonic(), 10.0, event)

    assert total == 0
    handler.assert_not_called()


def test_download_worker_stops_when_deadline_passes_mid_stream() -> None:
    def slow_body() -> Iterator[bytes]:
        yield b"x" * CHUNK_SIZE_BYTES
        time.sleep(0.3)  # outlasts the 0.1 s test length before the next chunk arrives
        yield b"x" * CHUNK_SIZE_BYTES

    with _client(lambda _: httpx2.Response(200, content=slow_body())) as client:
        total = download_worker(client, httpx2.Request("GET", "http://example.com/a"), time.monotonic(), 0.1)

    assert total == CHUNK_SIZE_BYTES


def test_download_worker_stops_when_shutdown_requested_mid_stream() -> None:
    event = threading.Event()

    def handler(_: httpx2.Request) -> httpx2.Response:
        event.set()
        return httpx2.Response(200, content=b"x" * 100_000)

    with _client(handler) as client:
        total = download_worker(client, httpx2.Request("GET", "http://example.com/a"), time.monotonic(), 10.0, event)

    assert total == 0


def test_download_worker_absorbs_network_errors() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("refused", request=request)

    with _client(handler) as client:
        total = download_worker(client, httpx2.Request("GET", "http://example.com/a"), time.monotonic(), 10.0)

    assert total == 0


# --- upload_worker ---


def test_upload_worker_sends_full_body_and_reports_bytes() -> None:
    received: list[bytes] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        received.append(request.read())
        return httpx2.Response(200)

    payload = _payload(CHUNK_SIZE_BYTES + 500)

    with _client(handler) as client:
        sent = upload_worker(client, _upload_request(payload), payload)

    assert sent == payload.length
    assert len(received[0]) == payload.length
    assert received[0].startswith(UPLOAD_BODY_PREFIX)


def test_upload_worker_skips_when_deadline_already_passed() -> None:
    handler = MagicMock()
    payload = HTTPUploaderData(length=100, start_time=time.monotonic() - 100, timeout=10.0)

    with _client(handler) as client:
        sent = upload_worker(client, _upload_request(payload), payload)

    assert sent == 0
    handler.assert_not_called()


def test_upload_worker_skips_when_shutdown_already_requested() -> None:
    event = threading.Event()
    event.set()
    handler = MagicMock()
    payload = _payload(100, event=event)

    with _client(handler) as client:
        sent = upload_worker(client, _upload_request(payload), payload, event)

    assert sent == 0
    handler.assert_not_called()


class _CutOffUpload(HTTPUploaderData):
    """Runs `action` after each chunk is read, so the body is cut off mid-stream."""

    def __init__(self, length: int, action: Callable[[], None], event: threading.Event | None = None) -> None:
        super().__init__(length=length, start_time=time.monotonic(), timeout=60.0, shutdown_event=event)
        self._action = action

    def read(self, n: int = -1) -> bytes:
        chunk = super().read(n)
        self._action()
        return chunk


def test_upload_worker_reports_partial_bytes_when_shutdown_mid_body() -> None:
    event = threading.Event()
    payload = _CutOffUpload(CHUNK_SIZE_BYTES * 5, event.set, event)

    with _client(lambda _: httpx2.Response(200)) as client:
        sent = upload_worker(client, _upload_request(payload), payload, event)

    assert sent == CHUNK_SIZE_BYTES


def test_upload_worker_reports_partial_bytes_on_connection_drop_mid_body() -> None:
    def drop() -> None:
        raise httpx2.WriteError("connection reset")

    payload = _CutOffUpload(CHUNK_SIZE_BYTES * 5, drop)

    with _client(lambda _: httpx2.Response(200)) as client:
        sent = upload_worker(client, _upload_request(payload), payload)

    assert sent == CHUNK_SIZE_BYTES


def test_upload_worker_reports_bytes_when_server_errors_after_full_body() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadError("connection reset", request=request)

    payload = _payload(CHUNK_SIZE_BYTES * 2)

    with _client(handler) as client:
        sent = upload_worker(client, _upload_request(payload), payload)

    assert sent == payload.length
