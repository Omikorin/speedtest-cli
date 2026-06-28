from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("speedtest-cli-ng")
except PackageNotFoundError:
    __version__ = "unknown"
