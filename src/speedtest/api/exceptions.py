"""
Exceptions raised by the speedtest.net API library.
"""

__all__ = [
    "ApiError",
    "BestServerFailureError",
    "ConfigFetchError",
    "InvalidServerError",
    "NoMatchedServerError",
    "ShareError",
    "UploadTimeoutError",
]


class ApiError(Exception):
    """Base class for every error the library raises on purpose."""


class ConfigFetchError(ApiError):
    """The configuration could not be retrieved or parsed."""


class InvalidServerError(ApiError):
    """A server cannot be tested because its description is incomplete."""


class NoMatchedServerError(ApiError):
    """No server matched when filtering."""


class BestServerFailureError(ApiError):
    """Unable to determine the best server."""


class ShareError(ApiError):
    """A share link could not be created."""


class UploadTimeoutError(ApiError):
    """
    The test length was reached during an upload.

    Used to ensure the upload halts when no additional data should be sent.
    """
