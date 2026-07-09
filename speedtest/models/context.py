import argparse
import threading
from dataclasses import dataclass

from speedtest.exceptions import SpeedtestCLIError
from speedtest.models.config import SpeedtestConfig


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
    units: tuple[str, int]  # e.g., ("b", 1) or ("B", 8)

    # Populated dynamically after initialization
    api_config: SpeedtestConfig | None = None

    # The global cancellation token for graceful exits
    shutdown_event: threading.Event | None = None

    def __post_init__(self) -> None:
        """Self-validating domain logic executed immediately after instantiation."""

        if self.threads < 1:
            raise SpeedtestCLIError("Invalid configuration: Thread count must be at least 1.")

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "RunContext":
        """Map raw argparse namespace into a validated domain context."""

        if args.single:
            threads = 1
        elif getattr(args, "threads", None) is not None:
            threads = args.threads
        else:
            threads = 4

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
            units=args.units,
        )
