"""Core CLI utilities for usecli.

This module provides core functionality for the usecli CLI including:
- Color constants and styling
- Custom exception classes with Rich formatting
- Centralized error handling
- Parameter validators
"""

from __future__ import annotations

import sys
from importlib import import_module

from usecli.cli.config.colors import COLOR
from usecli.cli.core.error import ErrorHandler, confirm_or_exit, error_exit
from usecli.cli.core.exceptions import (
    UsecliBadParameter,
    UsecliConfigError,
    UsecliError,
    UsecliUsageError,
    UsecliValidationError,
)
from usecli.cli.core.validators import (
    validate_command_name,
    validate_directory_exists,
    validate_email,
    validate_file_exists,
    validate_not_empty,
    validate_path_exists,
    validate_port,
    validate_positive_int,
    validate_url,
)

sys.modules.setdefault(__name__ + ".colors", import_module("usecli.cli.config.colors"))
sys.modules.setdefault(__name__ + ".list", import_module("usecli.cli.core.ui.list"))
sys.modules.setdefault(__name__ + ".title", import_module("usecli.cli.core.ui.title"))
sys.modules.setdefault(
    __name__ + ".error_handler", import_module("usecli.cli.core.error.handler")
)

__all__ = [
    # Colors
    "COLOR",
    # Exceptions
    "UsecliError",
    "UsecliUsageError",
    "UsecliBadParameter",
    "UsecliConfigError",
    "UsecliValidationError",
    # Error handling
    "ErrorHandler",
    "error_exit",
    "confirm_or_exit",
    # Validators
    "validate_not_empty",
    "validate_command_name",
    "validate_path_exists",
    "validate_file_exists",
    "validate_directory_exists",
    "validate_email",
    "validate_url",
    "validate_positive_int",
    "validate_port",
]
