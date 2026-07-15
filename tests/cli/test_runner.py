"""
Tests for the main CLI orchestrator.
"""

import signal
from unittest.mock import MagicMock, patch

from speedtest.cli.runner import _register_shutdown_handler, shell
from speedtest.exceptions import CLIError
from speedtest.models import ApiConfig, RunContext, Server
from speedtest.utils import ExitStatus


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
