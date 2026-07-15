"""
Tests for the RunContext domain model.
"""

import argparse

import pytest
from speedtest.exceptions import CLIError
from speedtest.models import RunContext


def _create_mock_args(**kwargs: bool | int | tuple[str, int] | None) -> argparse.Namespace:
    """Helper to generate a mock argparse.Namespace with default values."""

    defaults: dict[str, bool | int | tuple[str, int] | None] = {
        "list": False,
        "debug": False,
        "json": False,
        "server": None,
        "no_download": False,
        "no_upload": False,
        "single": False,
        "threads": None,
        "share": False,
        "units": ("b", 1),
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_run_context_post_init_validation() -> None:
    """Test that __post_init__ catches invalid thread counts."""

    valid_ctx = RunContext(
        list_servers_only=False,
        debug_mode=False,
        is_quiet=False,
        target_server_id=None,
        no_download=False,
        no_upload=False,
        threads=1,
        share=False,
        json_output=False,
        unit_name="b",
        unit_divisor=1,
    )
    assert valid_ctx.threads == 1

    with pytest.raises(CLIError, match="Thread count must be at least 1"):
        RunContext(
            list_servers_only=False,
            debug_mode=False,
            is_quiet=False,
            target_server_id=None,
            no_download=False,
            no_upload=False,
            threads=0,  # Invalid
            share=False,
            json_output=False,
            unit_name="b",
            unit_divisor=1,
        )


def test_run_context_from_args_default_threads() -> None:
    """Test mapping standard arguments where thread count defaults to 4."""

    args = _create_mock_args(list=True, debug=True, server=1234, units=("B", 8))

    ctx = RunContext.from_args(args)

    assert ctx.list_servers_only is True
    assert ctx.debug_mode is True
    assert ctx.target_server_id == 1234

    assert ctx.unit_name == "B"
    assert ctx.unit_divisor == 8

    assert ctx.threads == 4


def test_run_context_from_args_single_thread() -> None:
    """Test that --single flag properly overrides thread count to 1."""

    args = _create_mock_args(single=True)
    ctx = RunContext.from_args(args)

    assert ctx.threads == 1


def test_run_context_from_args_custom_threads() -> None:
    """Test that --threads flag explicitly sets the thread count."""

    args = _create_mock_args(threads=16)
    ctx = RunContext.from_args(args)

    assert ctx.threads == 16


def test_run_context_from_args_json_quiet_mode() -> None:
    """Test that the --json flag simultaneously sets json_output and is_quiet."""

    args = _create_mock_args(json=True)
    ctx = RunContext.from_args(args)

    assert ctx.json_output is True
    assert ctx.is_quiet is True
