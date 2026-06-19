"""
speedtest-cli: Next generation CLI for testing internet bandwidth using speedtest.net

"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("speedtest-cli-ng")
except PackageNotFoundError:
    __version__ = "unknown"

__date__ = "2026-06-10"
__author__ = "Michał Korczak"
__licence__ = "Apache License, Version 2.0"
