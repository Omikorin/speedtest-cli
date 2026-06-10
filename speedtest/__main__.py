"""The main entry point."""

import sys

from speedtest.cli import shell
from speedtest.exceptions import SpeedtestException


def main():
    try:
        shell()
    except KeyboardInterrupt:
        print("Cancelling...", file=sys.stderr)
    except (SpeedtestException, SystemExit) as e:
        # Ignore a successful exit, or argparse exit
        if getattr(e, "code", 1) not in (0, 2):
            msg = "%s" % e
            if not msg:
                msg = "%r" % e
            raise SystemExit("ERROR: %s" % msg)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    main()
