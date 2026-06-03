"""UI helpers for usecli CLI."""

from __future__ import annotations

import click

from usecli.cli.config.colors import COLOR, bold, style
from usecli.cli.core.ui.list import list_commands
from usecli.cli.core.ui.title import get_project_name, print_title


def is_click_group(obj: object) -> bool:
    """Check if an object is a Click group (has subcommands).

    Works with both standard click.Group and Typer's vendored click
    (TyperGroup in typer>=0.26 no longer extends click.Group directly).
    """
    return isinstance(obj, click.Group) or (
        hasattr(obj, "commands") and isinstance(getattr(obj, "commands", None), dict)
    )


__all__ = [
    "COLOR",
    "bold",
    "is_click_group",
    "list_commands",
    "print_title",
    "get_project_name",
    "style",
]
