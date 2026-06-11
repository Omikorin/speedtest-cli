"""
Speedtest-related exceptions.
"""

__all__ = [
    "SpeedtestException",
    "SpeedtestCLIError",
    "SpeedtestHTTPError",
    "SpeedtestConfigError",
    "SpeedtestServersError",
    "ConfigRetrievalError",
    "ServersRetrievalError",
    "InvalidServerIDType",
    "NoMatchedServers",
    "ShareResultsConnectFailure",
    "ShareResultsSubmitFailure",
    "SpeedtestUploadTimeout",
    "SpeedtestBestServerFailure",
    "SpeedtestMissingBestServer",
]


class SpeedtestException(Exception):
    """Base exception for this module."""


class SpeedtestCLIError(SpeedtestException):
    """Generic exception for raising errors during CLI operation."""


class SpeedtestHTTPError(SpeedtestException):
    """Base HTTP exception for this module."""


class SpeedtestConfigError(SpeedtestException):
    """Configuration XML is invalid."""


class SpeedtestServersError(SpeedtestException):
    """Servers XML is invalid."""


class ConfigRetrievalError(SpeedtestHTTPError):
    """Could not retrieve config.php."""


class ServersRetrievalError(SpeedtestHTTPError):
    """Could not retrieve speedtest-servers.php."""


class InvalidServerIDType(SpeedtestException):
    """Server ID used for filtering was not an integer."""


class NoMatchedServers(SpeedtestException):
    """No servers matched when filtering."""


class ShareResultsConnectFailure(SpeedtestException):
    """Could not connect to speedtest.net API to POST results."""


class ShareResultsSubmitFailure(SpeedtestException):
    """
    Unable to successfully POST results to speedtest.net API after
    connection.
    """


class SpeedtestUploadTimeout(SpeedtestException):
    """
    testlength configuration reached during upload.

    Used to ensure the upload halts when no additional data should be sent.
    """


class SpeedtestBestServerFailure(SpeedtestException):
    """Unable to determine best server."""


class SpeedtestMissingBestServer(SpeedtestException):
    """get_best_server not called or not able to determine best server."""
