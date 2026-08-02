"""UI helpers for usecli CLI.

Keep package imports light; load rich list/title helpers only when requested.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "COLOR",
    "bold",
    "get_project_name",
    "is_click_group",
    "list_commands",
    "print_title",
    "style",
]

_EXPORT_MODULES = {
    "COLOR": "usecli.cli.config.colors",
    "bold": "usecli.cli.config.colors",
    "style": "usecli.cli.config.colors",
    "list_commands": "usecli.cli.core.ui.list",
    "print_title": "usecli.cli.core.ui.title",
    "get_project_name": "usecli.cli.core.ui.title",
}


def is_click_group(obj: object) -> bool:
    """Check if an object behaves like a Click group."""
    import click

    return isinstance(obj, click.Group) or (
        hasattr(obj, "commands") and isinstance(getattr(obj, "commands", None), dict)
    )


def __getattr__(name: str) -> Any:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value
