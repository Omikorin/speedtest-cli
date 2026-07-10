import argparse
import threading
from dataclasses import dataclass

from speedtest.exceptions import CLIError

from .config import ApiConfig


@dataclass(kw_only=True)
class RunContext:
    # Execution modes
    list_servers_only: bool
    debug_mode: bool
    is_quiet: bool

    # Test parameters
    target_server_id: int | None
    no_download: bool
    no_upload: bool
    threads: int

    # Output
    share: bool
    json_output: bool
    unit_name: str
    unit_divisor: int

    # Populated dynamically after initialization
    api_config: ApiConfig | None = None

    # The global cancellation token for graceful exits
    shutdown_event: threading.Event | None = None

    def __post_init__(self) -> None:
        """Self-validating domain logic executed immediately after instantiation."""

        if self.threads < 1:
            raise CLIError("Invalid configuration: Thread count must be at least 1.")

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> RunContext:
        """Map raw argparse namespace into a validated domain context."""

        if args.single:
            threads = 1
        elif getattr(args, "threads", None) is not None:
            threads = args.threads
        else:
            threads = 4

        unit_name, unit_divisor = args.units

        return cls(
            list_servers_only=args.list,
            debug_mode=args.debug,
            is_quiet=args.json,
            target_server_id=args.server,
            no_download=args.no_download,
            no_upload=args.no_upload,
            threads=threads,
            share=args.share,
            json_output=args.json,
            unit_name=unit_name,
            unit_divisor=unit_divisor,
        )
