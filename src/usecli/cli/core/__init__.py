"""Core CLI utilities for usecli.

Exports are loaded lazily so importing submodules such as
``usecli.cli.core.base_command`` does not eagerly import Rich error handlers,
validators, and UI helpers on every CLI startup.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "COLOR",
    "UsecliError",
    "UsecliUsageError",
    "UsecliBadParameter",
    "UsecliConfigError",
    "UsecliValidationError",
    "ErrorHandler",
    "error_exit",
    "confirm_or_exit",
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

_EXPORT_MODULES = {
    "COLOR": "usecli.cli.config.colors",
    "UsecliError": "usecli.cli.core.exceptions",
    "UsecliUsageError": "usecli.cli.core.exceptions",
    "UsecliBadParameter": "usecli.cli.core.exceptions",
    "UsecliConfigError": "usecli.cli.core.exceptions",
    "UsecliValidationError": "usecli.cli.core.exceptions",
    "ErrorHandler": "usecli.cli.core.error",
    "error_exit": "usecli.cli.core.error",
    "confirm_or_exit": "usecli.cli.core.error",
    "validate_not_empty": "usecli.cli.core.validators",
    "validate_command_name": "usecli.cli.core.validators",
    "validate_path_exists": "usecli.cli.core.validators",
    "validate_file_exists": "usecli.cli.core.validators",
    "validate_directory_exists": "usecli.cli.core.validators",
    "validate_email": "usecli.cli.core.validators",
    "validate_url": "usecli.cli.core.validators",
    "validate_positive_int": "usecli.cli.core.validators",
    "validate_port": "usecli.cli.core.validators",
}


def __getattr__(name: str) -> Any:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
