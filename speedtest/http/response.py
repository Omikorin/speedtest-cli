"""
Response reading and gzip decoding
"""

import gzip
import shutil
from http.client import HTTPResponse
from io import BytesIO
from typing import Any

__all__ = [
    "GzipDecodedResponse",
    "get_response_stream",
]


class GzipDecodedResponse(gzip.GzipFile):
    """A file-like object to decode a response encoded with the gzip method."""

    def __init__(self, response: Any):
        self.io = BytesIO()
        shutil.copyfileobj(response, self.io)
        self.io.seek(0)
        super().__init__(mode="rb", fileobj=self.io)

    def close(self) -> None:
        try:
            super().close()
        finally:
            self.io.close()


def get_response_stream(response: HTTPResponse) -> HTTPResponse | GzipDecodedResponse:
    """Return a Gzip reader if ``Content-Encoding`` is ``gzip``, otherwise the response itself."""

    if response.getheader("content-encoding") == "gzip":
        return GzipDecodedResponse(response)

    return response
