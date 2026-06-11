"""
The main entry point. Invoke as `speedtest-cli` or `python -m speedtest`.
"""

import sys

from speedtest.exceptions import SpeedtestException
from speedtest.status import ExitStatus
from speedtest.utils import printer


def main() -> int:
    try:
        from speedtest.cli import shell

        exit_status = shell()

    except KeyboardInterrupt:
        printer("Stopped by user", error=True)
        exit_status = ExitStatus.ERROR_CTRL_C

    except SpeedtestException as e:
        code = getattr(e, "code", 1)

        if code not in (ExitStatus.SUCCESS, ExitStatus.ERROR_CTRL_C):
            msg = str(e) or repr(e)
            raise SystemExit(f"ERROR: {msg}") from e

        exit_status = code

    return getattr(exit_status, "value", exit_status)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

    sys.exit(main())
