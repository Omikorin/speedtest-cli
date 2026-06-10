"""
The main entry point.

"""

import sys


def main():
    try:
        from speedtest.cli import shell

        shell()
    except KeyboardInterrupt:
        from speedtest.status import ExitStatus

        print("Stopping speedtest-cli...")

        exit_status = ExitStatus.ERROR_CTRL_C
    except (SpeedtestException, SystemExit) as e:
        # TODO: Rework
        from speedtest.exceptions import SpeedtestException

        # Ignore a successful exit, or argparse exit
        if getattr(e, "code", 1) not in (0, 2):
            msg = "%s" % e
            if not msg:
                msg = "%r" % e
            raise SystemExit("ERROR: %s" % msg)

    return exit_status.value


if __name__ == "__main__":
    # TODO: Check if this is needed
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
