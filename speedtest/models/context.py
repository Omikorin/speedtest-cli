import argparse
from dataclasses import dataclass

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
    units: tuple[str, int]  # e.g., ("bit", 1) or ("byte", 8)

    # API payload
    api_config: SpeedtestConfig | None = None

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "RunContext":
        """
        Consumes the raw argparse namespace and reconciles the final application state.
        """

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
