"""
Consolidated exception tuples for network operations.
"""

import ssl
from http.client import HTTPException

from speedtest.exceptions import SpeedtestUploadTimeout

__all__ = [
    "HTTP_ERRORS",
    "UPLOAD_ERRORS",
]

HTTP_ERRORS = (
    OSError,
    HTTPException,
    ssl.CertificateError,
)

UPLOAD_ERRORS = (*HTTP_ERRORS, SpeedtestUploadTimeout)
