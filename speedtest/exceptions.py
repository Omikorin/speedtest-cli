"""
Speedtest-related exceptions.
"""

__all__ = [
    "NoMatchedServer",
    "SpeedtestBestServerFailure",
    "SpeedtestCLIError",
    "SpeedtestException",
    "SpeedtestUploadTimeout",
]


class SpeedtestException(Exception):
    """Base exception for this module."""


class SpeedtestCLIError(SpeedtestException):
    """Generic exception for raising errors during CLI operation."""


class NoMatchedServer(SpeedtestException):
    """No server matched when filtering."""


class SpeedtestUploadTimeout(SpeedtestException):
    """
    testlength configuration reached during upload.

    Used to ensure the upload halts when no additional data should be sent.
    """


class SpeedtestBestServerFailure(SpeedtestException):
    """Unable to determine best server."""
