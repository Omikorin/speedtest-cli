"""
Program exit status codes.

"""

from enum import IntEnum, unique


@unique
class ExitStatus(IntEnum):
    """Exit status codes constants"""

    SUCCESS = 0
    ERROR = 1

    # 128+2 SIGINT (idea from httpie)
    # <http://www.tldp.org/LDP/abs/html/exitcodes.html>
    ERROR_CTRL_C = 130
