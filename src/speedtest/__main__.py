"""
The main entry point. Invoke as `speedtest-cli` or `python -m speedtest`.
"""

import sys

from speedtest.cli import shell
from speedtest.exceptions import SpeedtestError
from speedtest.utils import ExitStatus, logger


def main() -> int:
    """Execute the CLI and return an integer exit status."""

    try:
        return shell()

    except KeyboardInterrupt:
        logger.error("Stopped by user")
        return ExitStatus.ERROR_CTRL_C.value

    except SpeedtestError as e:
        code = getattr(e, "code", ExitStatus.ERROR.value)

        if code not in (ExitStatus.SUCCESS.value, ExitStatus.ERROR_CTRL_C.value):
            msg = str(e) or repr(e)
            logger.error(msg)

        return int(code)

    except Exception:
        logger.exception("An unexpected error occurred.")
        return ExitStatus.ERROR.value


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
