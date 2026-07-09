"""
Speedtest-related exceptions.
"""

__all__ = [
    "BestServerFailureError",
    "CLIError",
    "NoMatchedServerError",
    "SpeedtestError",
    "UploadTimeoutError",
]


class SpeedtestError(Exception):
    """Base exception for this module."""


class CLIError(SpeedtestError):
    """Generic exception for raising errors during CLI operation."""


class NoMatchedServerError(SpeedtestError):
    """No server matched when filtering."""


class UploadTimeoutError(SpeedtestError):
    """
    testlength configuration reached during upload.

    Used to ensure the upload halts when no additional data should be sent.
    """


class BestServerFailureError(SpeedtestError):
    """Unable to determine best server."""
