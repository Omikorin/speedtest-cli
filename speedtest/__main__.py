"""
The main entry point. Invoke as `speedtest-cli` or `python -m speedtest`.
"""

import sys

from speedtest.exceptions import SpeedtestException
from speedtest.utils.logger import logger
from speedtest.utils.status import ExitStatus


def main() -> int:
    try:
        from speedtest.cli.main import shell

        exit_status = shell()

    except KeyboardInterrupt:
        logger.error("Stopped by user")
        exit_status = ExitStatus.ERROR_CTRL_C

    except SpeedtestException as e:
        code = getattr(e, "code", 1)

        if code not in (ExitStatus.SUCCESS, ExitStatus.ERROR_CTRL_C):
            msg = str(e) or repr(e)
            raise SystemExit(f"ERROR: {msg}") from e

        exit_status = code

    return getattr(exit_status, "value", exit_status)


if __name__ == "__main__":
    sys.exit(main())
