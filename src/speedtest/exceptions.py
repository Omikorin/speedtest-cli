"""
Exceptions of the command-line program.
"""

__all__ = ["CLIError", "SpeedtestError"]


class SpeedtestError(Exception):
    """Base exception for the program."""


class CLIError(SpeedtestError):
    """Generic exception for raising errors during CLI operation."""
