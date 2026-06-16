"""
speedtest-cli: Command line interface for testing internet bandwidth using speedtest.net

This project is a continuation/fork of the original "speedtest-cli" by Matt Martz.

Licensed under the Apache License, Version 2.0.

Copyright (c) 2026 Michał Korczak
Copyright (c) 2012-2026 Matt Martz

"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("speedtest-cli")
except PackageNotFoundError:
    __version__ = "unknown"

__date__ = "2026-06-10"
__author__ = "Michał Korczak"
__licence__ = "Apache License, Version 2.0"
