"""
Tests for the SpeedtestClient orchestration.
"""

import json
from dataclasses import replace
from hashlib import md5
from unittest.mock import MagicMock, patch

import httpx2
import pytest
from speedtest.client import SpeedtestClient
from speedtest.exceptions import CLIError, NoMatchedServerError
from speedtest.models import ApiConfig, RunContext, Server, SpeedtestResult

SHARE_URL = "https://www.speedtest.net/api/results.php"


@pytest.fixture
def client() -> SpeedtestClient:
    return SpeedtestClient()


def _response(status: int = 200, *, text: str | None = None, json: object = None) -> httpx2.Response:
    return httpx2.Response(status, text=text, json=json, request=httpx2.Request("POST", SHARE_URL))


def _sent_payload(mock_post: MagicMock) -> dict[str, object]:
    return json.loads(mock_post.call_args.kwargs["content"])


# --- get_target_servers ---


def test_get_target_servers_sorts_by_distance_and_limits(
    client: SpeedtestClient, mock_api_config: ApiConfig, mock_server: Server
) -> None:
    mock_api_config.servers = [replace(mock_server, id=i, distance=d) for i, d in [(1, 50), (2, 5), (3, 20), (4, 1)]]

    result = client.get_target_servers(mock_api_config, limit=3)

    assert [s.id for s in result] == [4, 2, 3]


def test_get_target_servers_filters_by_id(
    client: SpeedtestClient, mock_api_config: ApiConfig, mock_server: Server
) -> None:
    mock_api_config.servers = [replace(mock_server, id=1, distance=5), replace(mock_server, id=2, distance=1)]

    result = client.get_target_servers(mock_api_config, target_id=1)

    assert [s.id for s in result] == [1]


def test_get_target_servers_unknown_id_raises(
    client: SpeedtestClient, mock_api_config: ApiConfig, mock_server: Server
) -> None:
    mock_api_config.servers = [mock_server]

    with pytest.raises(NoMatchedServerError, match="999"):
        client.get_target_servers(mock_api_config, target_id=999)


# --- select_best_server ---


def test_select_best_server_empty_list_raises(client: SpeedtestClient) -> None:
    with pytest.raises(CLIError, match="No servers provided"):
        client.select_best_server([])


@patch("speedtest.client.get_best_server")
def test_select_best_server_returns_pinger_result(
    mock_best: MagicMock, client: SpeedtestClient, mock_server: Server
) -> None:
    mock_best.return_value = (mock_server, 12.5)

    assert client.select_best_server([mock_server]) == (mock_server, 12.5)


@patch("speedtest.client.get_best_server")
def test_select_best_server_falsy_result_raises(
    mock_best: MagicMock, client: SpeedtestClient, mock_server: Server
) -> None:
    mock_best.return_value = (None, 0.0)

    with pytest.raises(CLIError, match="Failed to identify"):
        client.select_best_server([mock_server])


# --- download / upload ---


@patch("speedtest.client.run_download_test", return_value=(10, 80.0))
def test_download_delegates_with_server_url(
    mock_run: MagicMock, client: SpeedtestClient, mock_server: Server, mock_run_context: RunContext
) -> None:
    assert client.download(mock_server, mock_run_context) == (10, 80.0)
    mock_run.assert_called_once_with(best_server_url=mock_server.url, ctx=mock_run_context)


@patch("speedtest.client.run_upload_test", return_value=(20, 160.0))
def test_upload_delegates_with_server_url(
    mock_run: MagicMock, client: SpeedtestClient, mock_server: Server, mock_run_context: RunContext
) -> None:
    assert client.upload(mock_server, mock_run_context) == (20, 160.0)
    mock_run.assert_called_once_with(best_server_url=mock_server.url, ctx=mock_run_context)


@pytest.mark.parametrize("method", ["download", "upload"])
def test_transfer_without_server_url_raises(
    method: str, client: SpeedtestClient, mock_server: Server, mock_run_context: RunContext
) -> None:
    server = replace(mock_server, url="")
    transfer = getattr(client, method)

    with pytest.raises(CLIError, match="missing a valid URL"):
        transfer(server, mock_run_context)


# --- generate_share_link ---


@patch("speedtest.client.httpx2.post")
def test_share_link_success_sends_signed_payload(
    mock_post: MagicMock, client: SpeedtestClient, mock_result: SpeedtestResult, mock_api_config: ApiConfig
) -> None:
    mock_post.return_value = _response(json={"resultid": 777, "hash_key_id": "abc"})

    link = client.generate_share_link(mock_result, mock_api_config)

    assert link == "https://www.speedtest.net/result/777.png"

    payload = _sent_payload(mock_post)
    # 15.5 ms rounds to 16; 100/50 Mb/s become 100000/50000 kbps.
    assert payload["ping"] == 16
    assert payload["download"] == 100_000
    assert payload["upload"] == 50_000
    assert payload["hash"] == md5(b"16-50000-100000-817d699764d33f89c").hexdigest()
    assert payload["serverid"] == 1234
    assert payload["guid"] == "dummy-guid"
    assert payload["clientip"] == "1.1.1.1"
    assert payload["ispName"] == "Acme Internet"
    assert payload["configs"] == {"host": "speedtest.example.com", "port": 8080}

    sent = mock_post.call_args
    assert sent.args[0] == SHARE_URL
    assert sent.kwargs["headers"]["Content-Type"] == "application/json;charset=UTF-8"
    assert sent.kwargs["headers"]["Origin"] == "https://www.speedtest.net"


@patch("speedtest.client.httpx2.post")
def test_share_link_uses_default_port_when_host_has_none(
    mock_post: MagicMock, client: SpeedtestClient, mock_result: SpeedtestResult, mock_api_config: ApiConfig
) -> None:
    assert mock_result.server is not None
    mock_result.server = replace(mock_result.server, host="speedtest.example.com")
    mock_post.return_value = _response(json={"resultid": 1})

    client.generate_share_link(mock_result, mock_api_config)

    assert _sent_payload(mock_post)["configs"] == {"host": "speedtest.example.com", "port": 8080}


@patch("speedtest.client.httpx2.post")
def test_share_link_omits_missing_speeds(
    mock_post: MagicMock, client: SpeedtestClient, mock_result: SpeedtestResult, mock_api_config: ApiConfig
) -> None:
    mock_result.download_bps = None
    mock_result.upload_bps = None
    mock_post.return_value = _response(json={"resultid": 1})

    client.generate_share_link(mock_result, mock_api_config)

    payload = _sent_payload(mock_post)
    assert "download" not in payload
    assert "upload" not in payload
    assert payload["hash"] == md5(b"16-0-0-817d699764d33f89c").hexdigest()


def test_share_link_requires_ping(
    client: SpeedtestClient, mock_result: SpeedtestResult, mock_api_config: ApiConfig
) -> None:
    mock_result.ping_ms = None

    with pytest.raises(CLIError, match="missing test results"):
        client.generate_share_link(mock_result, mock_api_config)


def test_share_link_requires_server(
    client: SpeedtestClient, mock_result: SpeedtestResult, mock_api_config: ApiConfig
) -> None:
    mock_result.server = None

    with pytest.raises(CLIError, match="missing test results"):
        client.generate_share_link(mock_result, mock_api_config)


@patch("speedtest.client.httpx2.post")
def test_share_link_http_error_status(
    mock_post: MagicMock, client: SpeedtestClient, mock_result: SpeedtestResult, mock_api_config: ApiConfig
) -> None:
    mock_post.return_value = _response(403, text="403 Forbidden")

    with pytest.raises(CLIError, match="HTTP 403"):
        client.generate_share_link(mock_result, mock_api_config)


@patch("speedtest.client.httpx2.post")
def test_share_link_network_error(
    mock_post: MagicMock, client: SpeedtestClient, mock_result: SpeedtestResult, mock_api_config: ApiConfig
) -> None:
    mock_post.side_effect = httpx2.ConnectError("boom")

    with pytest.raises(CLIError, match="Failed to connect to Share API"):
        client.generate_share_link(mock_result, mock_api_config)


@pytest.mark.parametrize(
    "response",
    [
        _response(text="not json"),
        _response(json=[]),  # what the API returns when the payload is rejected
        _response(json={"date": "11/8/2026"}),
        _response(json={"resultid": None}),
    ],
    ids=["invalid-json", "empty-list", "no-resultid", "null-resultid"],
)
@patch("speedtest.client.httpx2.post")
def test_share_link_unusable_response(
    mock_post: MagicMock,
    response: httpx2.Response,
    client: SpeedtestClient,
    mock_result: SpeedtestResult,
    mock_api_config: ApiConfig,
) -> None:
    mock_post.return_value = response

    with pytest.raises(CLIError, match="Could not parse result ID"):
        client.generate_share_link(mock_result, mock_api_config)
