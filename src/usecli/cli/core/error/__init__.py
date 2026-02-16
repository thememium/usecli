"""Error handling utilities for usecli CLI."""

from __future__ import annotations

from usecli.cli.core.error.handler import ErrorHandler
from usecli.cli.core.error.utils import confirm_or_exit, error_exit

__all__ = [
    "ErrorHandler",
    "error_exit",
    "confirm_or_exit",
]
