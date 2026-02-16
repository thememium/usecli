"""Exception classes for usecli CLI."""

from __future__ import annotations

from usecli.cli.core.exceptions.base import UsecliError
from usecli.cli.core.exceptions.config import UsecliConfigError
from usecli.cli.core.exceptions.usage import UsecliBadParameter, UsecliUsageError
from usecli.cli.core.exceptions.validation import UsecliValidationError

__all__ = [
    "UsecliError",
    "UsecliUsageError",
    "UsecliBadParameter",
    "UsecliConfigError",
    "UsecliValidationError",
]
