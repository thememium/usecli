"""Exception classes for usecli CLI."""

from __future__ import annotations

__all__ = [
    "UsecliError",
    "UsecliUsageError",
    "UsecliBadParameter",
    "UsecliConfigError",
    "UsecliValidationError",
]

_EXPORT_MODULES = {
    "UsecliError": "usecli.cli.core.exceptions.base",
    "UsecliUsageError": "usecli.cli.core.exceptions.usage",
    "UsecliBadParameter": "usecli.cli.core.exceptions.usage",
    "UsecliConfigError": "usecli.cli.core.exceptions.config",
    "UsecliValidationError": "usecli.cli.core.exceptions.validation",
}


def __getattr__(name: str):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
