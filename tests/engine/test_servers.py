"""
Tests for server latency ranking.
"""

import socket
from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest
from speedtest.engine.servers import _ping_server, find_fastest_server, get_best_server
from speedtest.exceptions import BestServerFailureError
from speedtest.models import Server

PENALTY_MS = 3600000.0


# --- _ping_server ---


def test_ping_server_without_url_is_penalised(mock_server: Server) -> None:
    _, latency = _ping_server(replace(mock_server, url=""))

    assert latency == PENALTY_MS


def test_ping_server_url_without_host_is_penalised(mock_server: Server) -> None:
    _, latency = _ping_server(replace(mock_server, url="http:///upload.php"))

    assert latency == PENALTY_MS


@patch("speedtest.engine.servers.socket.gethostbyname", side_effect=socket.gaierror)
def test_ping_server_dns_failure_is_penalised(_mock_dns: MagicMock, mock_server: Server) -> None:
    _, latency = _ping_server(mock_server)

    assert latency == PENALTY_MS


@pytest.mark.parametrize(
    ("url", "expected_port"),
    [
        ("http://speedtest.example.com/upload.php", 80),
        ("https://speedtest.example.com/upload.php", 443),
        ("http://speedtest.example.com:8080/upload.php", 8080),
    ],
)
@patch("speedtest.engine.servers.measure_tcp_latency")
@patch("speedtest.engine.servers.socket.gethostbyname", return_value="10.0.0.1")
def test_ping_server_averages_handshakes_on_resolved_port(
    _mock_dns: MagicMock, mock_latency: MagicMock, url: str, expected_port: int, mock_server: Server
) -> None:
    mock_latency.side_effect = [10.0, 20.0, 30.0]

    server, latency = _ping_server(replace(mock_server, url=url), pings=3)

    assert server.url == url
    assert latency == pytest.approx(20.0)
    assert [c.args for c in mock_latency.call_args_list] == [("10.0.0.1", expected_port)] * 3


@patch("speedtest.engine.servers.socket.gethostbyname", return_value="10.0.0.1")
def test_ping_server_zero_pings_is_penalised(_mock_dns: MagicMock, mock_server: Server) -> None:
    _, latency = _ping_server(mock_server, pings=0)

    assert latency == PENALTY_MS


# --- find_fastest_server ---


def test_find_fastest_server_returns_lowest_latency(mock_server: Server) -> None:
    slow = replace(mock_server, id=1)
    fast = replace(mock_server, id=2)

    assert find_fastest_server([(slow, 50.0), (fast, 5.0)]) == (fast, 5.0)


def test_find_fastest_server_empty_raises() -> None:
    with pytest.raises(BestServerFailureError, match="Unable to determine best server"):
        find_fastest_server([])


# --- get_best_server ---


def test_get_best_server_requires_servers() -> None:
    with pytest.raises(BestServerFailureError, match="No servers provided"):
        get_best_server([])


def test_get_best_server_picks_lowest_latency(mock_server: Server) -> None:
    servers = [replace(mock_server, id=i) for i in (1, 2, 3)]
    latencies = {1: 40.0, 2: 8.0, 3: 25.0}

    with patch("speedtest.engine.servers._ping_server", side_effect=lambda s: (s, latencies[s.id])):
        best, latency = get_best_server(servers)

    assert (best.id, latency) == (2, 8.0)


def test_get_best_server_skips_servers_whose_ping_raises(mock_server: Server) -> None:
    servers = [replace(mock_server, id=i) for i in (1, 2)]

    def ping(server: Server) -> tuple[Server, float]:
        if server.id == 1:
            raise OSError("network down")
        return server, 99.0

    with patch("speedtest.engine.servers._ping_server", side_effect=ping):
        best, _ = get_best_server(servers)

    assert best.id == 2


def test_get_best_server_all_pings_failing_raises(mock_server: Server) -> None:
    with (
        patch("speedtest.engine.servers._ping_server", side_effect=OSError("down")),
        pytest.raises(BestServerFailureError),
    ):
        get_best_server([mock_server])
