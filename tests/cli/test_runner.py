"""
Tests for the main CLI orchestrator.
"""

import logging
import signal
from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from speedtest.cli.runner import _register_shutdown_handler, shell
from speedtest.engine.config import ConfigFetchError
from speedtest.exceptions import CLIError
from speedtest.models import ApiConfig, RunContext, Server, SpeedtestResult
from speedtest.utils import ExitStatus


@pytest.fixture
def shell_env(
    mock_run_context: RunContext, mock_api_config: ApiConfig, mock_server: Server
) -> Iterator[SimpleNamespace]:
    """Run shell() against a fake client that returns fixed measurements."""

    with (
        patch("speedtest.cli.runner.parse_args"),
        patch("speedtest.cli.runner.RunContext.from_args", return_value=mock_run_context),
        patch("speedtest.cli.runner.get_config", return_value=mock_api_config) as get_config,
        patch("speedtest.cli.runner.SpeedtestClient") as client_class,
        patch("speedtest.cli.runner.console.status"),
    ):
        client = client_class.return_value
        client.get_target_servers.return_value = [mock_server]
        client.select_best_server.return_value = (mock_server, 15.5)
        client.download.return_value = (12_500_000, 100_000_000.0)
        client.upload.return_value = (6_250_000, 50_000_000.0)
        yield SimpleNamespace(client=client, get_config=get_config)


def test_register_shutdown_handler() -> None:
    """Test that the SIGINT handler correctly sets the event and raises KeyboardInterrupt."""

    with patch("speedtest.cli.runner.signal.signal") as mock_signal:
        shutdown_event = _register_shutdown_handler()
        assert mock_signal.call_count == 1

        handler_func = mock_signal.call_args[0][1]
        assert not shutdown_event.is_set()

        try:
            handler_func(signal.SIGINT, None)
        except KeyboardInterrupt:
            pass

        assert shutdown_event.is_set() is True


@patch("speedtest.cli.runner.SpeedtestClient")
@patch("speedtest.cli.runner.get_config")
@patch("speedtest.cli.runner.RunContext.from_args")
@patch("speedtest.cli.runner.parse_args")
@patch("speedtest.cli.runner.console.status")
def test_shell_successful_standard_run(
    mock_status: MagicMock,
    mock_parse: MagicMock,
    mock_context: MagicMock,
    mock_get_config: MagicMock,
    mock_client_class: MagicMock,
    mock_server: Server,
    mock_run_context: RunContext,
    mock_api_config: ApiConfig,
) -> None:
    """Test a full, standard run of the speedtest shell."""

    mock_context.return_value = mock_run_context
    mock_get_config.return_value = mock_api_config

    mock_client = mock_client_class.return_value
    mock_client.get_target_servers.return_value = [mock_server]
    mock_client.select_best_server.return_value = (mock_server, 15.5)
    mock_client.download.return_value = (12_500_000, 100_000_000.0)
    mock_client.upload.return_value = (6_250_000, 50_000_000.0)

    status = shell()

    assert status == ExitStatus.SUCCESS.value
    mock_client.get_target_servers.assert_called_once()
    mock_client.select_best_server.assert_called_once()
    mock_client.download.assert_called_once()
    mock_client.upload.assert_called_once()

    mock_client.generate_share_link.assert_not_called()  # --share was false


@patch("speedtest.cli.runner.print_server_list")
@patch("speedtest.cli.runner.SpeedtestClient")
@patch("speedtest.cli.runner.get_config")
@patch("speedtest.cli.runner.RunContext.from_args")
@patch("speedtest.cli.runner.parse_args")
@patch("speedtest.cli.runner.console.status")
def test_shell_list_servers_early_exit(
    mock_status: MagicMock,
    mock_parse: MagicMock,
    mock_context: MagicMock,
    mock_get_config: MagicMock,
    mock_client_class: MagicMock,
    mock_print_list: MagicMock,
    mock_run_context: RunContext,
    mock_api_config: ApiConfig,
) -> None:
    """Test that using --list fetches servers and exits early."""

    mock_run_context.list_servers_only = True
    mock_context.return_value = mock_run_context
    mock_get_config.return_value = mock_api_config
    mock_print_list.return_value = ExitStatus.SUCCESS.value
    mock_client = mock_client_class.return_value

    status = shell()

    assert status == ExitStatus.SUCCESS.value
    mock_client.get_target_servers.assert_called_once()
    mock_print_list.assert_called_once()

    # Verify it skipped the actual testing
    mock_client.select_best_server.assert_not_called()
    mock_client.download.assert_not_called()
    mock_client.upload.assert_not_called()
    mock_client.generate_share_link.assert_not_called()


@patch("speedtest.cli.runner.print_json")
@patch("speedtest.cli.runner.SpeedtestClient")
@patch("speedtest.cli.runner.get_config")
@patch("speedtest.cli.runner.RunContext.from_args")
@patch("speedtest.cli.runner.parse_args")
@patch("speedtest.cli.runner.console.status")
def test_shell_skips_transfers_and_prints_json(
    mock_status: MagicMock,
    mock_parse: MagicMock,
    mock_context: MagicMock,
    mock_get_config: MagicMock,
    mock_client_class: MagicMock,
    mock_print_json: MagicMock,
    mock_server: Server,
    mock_run_context: RunContext,
    mock_api_config: ApiConfig,
) -> None:
    """Test --no-download, --no-upload, --share, and --json modifiers."""

    mock_run_context.no_download = True
    mock_run_context.no_upload = True
    mock_run_context.share = True
    mock_run_context.json_output = True
    mock_context.return_value = mock_run_context
    mock_get_config.return_value = mock_api_config

    mock_client = mock_client_class.return_value
    mock_client.select_best_server.return_value = (mock_server, 15.5)
    mock_client.generate_share_link.return_value = "http://speedtest.example.com/result/987"

    status = shell()

    assert status == ExitStatus.SUCCESS.value

    mock_client.get_target_servers.assert_called_once()
    mock_client.select_best_server.assert_called_once()
    mock_print_json.assert_called_once()
    mock_client.generate_share_link.assert_called_once()

    # Verify it skipped the actual testing
    mock_client.download.assert_not_called()
    mock_client.upload.assert_not_called()


@patch("speedtest.cli.runner.get_config")
@patch("speedtest.cli.runner.RunContext.from_args")
@patch("speedtest.cli.runner.parse_args")
@patch("speedtest.cli.runner.console.status")
def test_shell_catches_cli_error(
    mock_status: MagicMock,
    mock_parse: MagicMock,
    mock_context: MagicMock,
    mock_get_config: MagicMock,
    mock_run_context: RunContext,
) -> None:
    """Test that a CLIError gracefully returns an ERROR status code."""

    mock_context.return_value = mock_run_context
    mock_get_config.side_effect = CLIError("Failed to fetch configuration.")

    status = shell()
    assert status == ExitStatus.ERROR.value


def test_shell_catches_config_fetch_error(shell_env: SimpleNamespace, caplog: pytest.LogCaptureFixture) -> None:
    """get_config raises ConfigFetchError, not CLIError, when speedtest.net refuses the request."""

    shell_env.get_config.side_effect = ConfigFetchError("HTTP 403: Failed to fetch config.")

    with caplog.at_level(logging.ERROR, logger="speedtest"):
        status = shell()

    assert status == ExitStatus.ERROR.value
    assert "HTTP 403" in caplog.text
    shell_env.client.select_best_server.assert_not_called()


def test_shell_logs_measurements_in_requested_units(
    shell_env: SimpleNamespace, mock_run_context: RunContext, caplog: pytest.LogCaptureFixture
) -> None:
    mock_run_context.unit_name = "B"
    mock_run_context.unit_divisor = 8

    with caplog.at_level(logging.INFO, logger="speedtest"):
        shell()

    messages = [r.getMessage() for r in caplog.records]
    assert "Latency: 15.50000 ms" in messages
    assert "Download: 12.50 MB/s (12.50 MB)" in messages
    assert "Upload: 6.25 MB/s (6.25 MB)" in messages


def test_shell_hands_measurements_and_share_url_to_json_output(
    shell_env: SimpleNamespace, mock_run_context: RunContext, mock_api_config: ApiConfig, mock_server: Server
) -> None:
    mock_run_context.share = True
    mock_run_context.json_output = True
    shell_env.client.generate_share_link.return_value = "https://www.speedtest.net/result/1.png"

    with patch("speedtest.cli.runner.print_json") as print_json:
        shell()

    results, config = print_json.call_args.args
    assert isinstance(results, SpeedtestResult)
    assert results.server == mock_server
    assert results.ping_ms == pytest.approx(15.5)
    assert results.download_bps == pytest.approx(100_000_000.0)
    assert results.upload_bytes == 6_250_000
    assert results.share_url == "https://www.speedtest.net/result/1.png"
    assert config is mock_api_config

    # The share call must receive the measured results and the client config.
    shared_results, shared_config = shell_env.client.generate_share_link.call_args.args
    assert shared_results is results
    assert shared_config is mock_api_config


def test_shell_ping_only_run_leaves_speeds_unset(shell_env: SimpleNamespace, mock_run_context: RunContext) -> None:
    mock_run_context.no_download = True
    mock_run_context.no_upload = True
    mock_run_context.json_output = True

    with patch("speedtest.cli.runner.print_json") as print_json:
        shell()

    results = print_json.call_args.args[0]
    assert results.ping_ms == pytest.approx(15.5)
    assert results.download_bps is None
    assert results.upload_bps is None


def test_shell_passes_target_server_id_to_client(shell_env: SimpleNamespace, mock_run_context: RunContext) -> None:
    mock_run_context.target_server_id = 52365

    shell()

    assert shell_env.client.get_target_servers.call_args.kwargs["target_id"] == 52365
