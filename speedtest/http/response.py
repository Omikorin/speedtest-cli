"""
Response reading and gzip decoding.
"""

import gzip
import io
from http.client import HTTPResponse

__all__ = ["get_response_stream"]


def get_response_stream(response: HTTPResponse) -> io.BufferedIOBase:
    """
    Return a streaming Gzip reader if ``Content-Encoding`` is ``gzip``,
    otherwise return the response stream itself.
    """

    encoding = response.getheader("content-encoding", "")

    if encoding and encoding.lower() == "gzip":
        return gzip.GzipFile(fileobj=response, mode="rb")

    return response
