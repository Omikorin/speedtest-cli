"""
The main entry point. Invoke as `speedtest-cli` or `python -m speedtest`.

"""

import sys

from speedtest.exceptions import SpeedtestException
from speedtest.status import ExitStatus


def main():
    try:
        from speedtest.cli import shell

        exit_status = shell()
    except KeyboardInterrupt:
        print("Stopping speedtest-cli...")

        exit_status = ExitStatus.ERROR_CTRL_C
    except SpeedtestException as e:
        # TODO: Rework

        if getattr(e, "code", 1) not in (ExitStatus.SUCCESS, ExitStatus.ERROR_CTRL_C):
            msg = "%s" % e
            if not msg:
                msg = "%r" % e
            raise SystemExit("ERROR: %s" % msg)

    return exit_status.value


if __name__ == "__main__":
    # TODO: Check if this is needed
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    sys.exit(main())
