"""
Consolidated error tuples
"""

import ssl
from http.client import BadStatusLine
from urllib.error import HTTPError, URLError

from speedtest.exceptions import SpeedtestUploadTimeout


__all__ = [
    "UPLOAD_ERRORS",
]


# Consolidating errors (OSError inherently covers socket.error and IOError)
HTTP_ERRORS = (
    HTTPError,
    URLError,
    OSError,
    ssl.SSLError,
    BadStatusLine,
    ssl.CertificateError,
)

UPLOAD_ERRORS = HTTP_ERRORS + (SpeedtestUploadTimeout,)
