"""
Identity of the library, used to build the HTTP User-Agent.
"""

from importlib.metadata import version

__all__ = ["__version__"]

__version__ = version("speedtest-cli-ng")
