# speedtest-cli

[![PyPI version](https://img.shields.io/pypi/v/speedtest-cli-ng.svg)](https://github.com/Omikorin/speedtest-cli)
[![PyPI license](https://img.shields.io/pypi/l/speedtest-cli-ng.svg)](https://github.com/Omikorin/speedtest-cli)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/speedtest-cli-ng.svg)](https://github.com/Omikorin/speedtest-cli)
<!-- [![GitHub  License](https://img.shields.io/github/license/Omikorin/speedtest-cli)](https://github.com/Omikorin/speedtest-cli/blob/main/LICENSE) -->
<!-- TODO: SonarQube, GitHub Actions? -->

Next generation CLI for testing internet bandwidth using speedtest.net

Rebuilt for modern Python 3.12+

## Getting started

### Installation

#### PyPI

TODO:

### Usage

To view the available options, run the help command:

```bash
speedtest-cli --help
```

```text
usage: speedtest-cli [-h] [-l] [-s SERVER] [--no-download] [--no-upload] [-t THREADS | --single]
                     [--share] [--bytes] [--csv | --json] [--csv-delimiter CSV_DELIMITER]
                     [--csv-header] [--source SOURCE] [--timeout TIMEOUT] [--debug] [--version]

Next generation CLI for testing internet bandwidth using speedtest.net.

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit

Core Options:
  -l, --list            Show available speedtest.net servers sorted by distance. (default: False)
  -s SERVER, --server SERVER
                        Specify a server id to test against. (default: None)

Transfer Modifiers:
  --no-download         Do not perform the download test. (default: False)
  --no-upload           Do not perform the upload test. (default: False)
  -t THREADS, --threads THREADS
                        Set the number of concurrent connections instead of using downloaded config. (default: None)
  --single              Use one concurrent connection. Simulates a typical file transfer. (default: False)

Output Options:
  --share               Generate and provide a URL to the speedtest.net share results image. (default: False)
  --bytes               Display values in bytes instead of bits. Does not affect image generation or JSON/CSV output. (default: ('bit', 1))
  --csv                 Suppress verbose output, only show basic information in CSV format. Speeds listed in bit/s. (default: False)
  --json                Suppress verbose output, only show basic information in JSON format. Speeds listed in bit/s. (default: False)
  --csv-delimiter CSV_DELIMITER
                        Single character delimiter to use in CSV output. (default: ,)
  --csv-header          Print CSV headers and exit. (default: False)

Connection Options:
  --source SOURCE       Bind a source IP address to use for connections. (default: None)
  --timeout TIMEOUT     HTTP timeout in seconds. (default: 10.0)
  --debug               Show verbose debugging output. (default: False)
```

## Development

### Requirements

- Python 3.12+
- uv 0.11+

### Setup project

This will install project's dependencies. Keep in mind that there are no runtime dependencies in production.

```bash
uv sync
```

### Basic workflow

```bash
# Run format
uv run ruff format --check .

# Run lint
uv run ruff check .

# Run typecheck
uv run pyright

# Run tests
uv run pytest
```

### Building

Build both sdist and wheel package:

```bash
uv run build
```

The output will be in the `dist/` directory.


## Acknowledgments

This project is a heavily refactored and modernized fork of the original [speedtest-cli](https://github.com/sivel/speedtest-cli) created by Matt Martz. While the codebase has been completely rewritten to support modern Python standards, concurrent thread pools, and memory-safe streaming, it was built upon the foundational concepts of the original tool.

## License

This project is licensed undeer the [Apache License 2.0](https://github.com/Omikorin/speedtest-cli/blob/main/LICENSE).

---

<p align="center">Made with 🩵 by Michał Korczak</p>

---
