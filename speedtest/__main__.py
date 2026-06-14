"""
The main entry point. Invoke as `speedtest-cli` or `python -m speedtest`.
"""

import sys

from speedtest.cli.main import shell
from speedtest.exceptions import SpeedtestException
from speedtest.utils.logger import logger
from speedtest.utils.status import ExitStatus


def main() -> int:
    """Execute the CLI and return an integer exit status."""

    try:
        exit_status = shell()

        return int(exit_status)

    except KeyboardInterrupt:
        logger.error("Stopped by user")
        return ExitStatus.ERROR_CTRL_C.value

    except SpeedtestException as e:
        code = getattr(e, "code", ExitStatus.ERROR.value)

        if code not in (ExitStatus.SUCCESS.value, ExitStatus.ERROR_CTRL_C.value):
            msg = str(e) or repr(e)
            logger.error(f"ERROR: {msg}")

        return int(code)

    except Exception as _e:
        logger.exception("An unexpected error occurred.")
        return ExitStatus.ERROR.value


if __name__ == "__main__":
    sys.exit(main())
