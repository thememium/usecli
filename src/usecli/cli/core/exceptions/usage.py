"""Usage and parameter errors for usecli CLI."""

from __future__ import annotations

import sys
from typing import IO

from click.core import Context as ClickContext
from click.exceptions import BadParameter, UsageError

def _lazy_console():
    from rich.console import Console
    return Console(stderr=True)


def _get_help_text_with_command_name(ctx: ClickContext) -> str:
    from usecli.cli.core.ui.title import get_script_command_name
    command_name = get_script_command_name(default=getattr(ctx, "info_name", None))
    if not command_name:
        return ctx.get_help()

    original_info_name = getattr(ctx, "info_name", None)
    try:
        ctx.info_name = command_name
        return ctx.get_help()
    finally:
        ctx.info_name = original_info_name


class UsecliUsageError(UsageError):
    """Usage error with styled output and full command help.

    Extends Click's UsageError to provide Rich-styled error messages
    and automatically display command help when an error occurs.
    """

    def show(self, file: IO[str] | None = None) -> None:
        """Display styled usage error with full command help.

        Args:
            file: Optional file to write to (defaults to stderr).
        """
        from usecli.cli.config.colors import COLOR
        console = _lazy_console()

        if file is None:
            file = sys.stderr

        error_prefix = f"[bold {COLOR.ERROR}]ERROR[/bold {COLOR.ERROR}]"
        error_msg = f"[bold {COLOR.ERROR}]{self.format_message()}[/bold {COLOR.ERROR}]"
        console.print(f"{error_prefix}  {error_msg}")

        if self.ctx:
            console.print()
            help_text = _get_help_text_with_command_name(self.ctx)
            console.print(help_text)


class UsecliBadParameter(BadParameter):
    """Parameter validation error with styled output.

    Use this in parameter callbacks for consistent error styling.
    Provides highlighted error boxes and command help on validation failures.
    """

    def show(self, file: IO[str] | None = None) -> None:
        """Display styled parameter error with command help.

        Args:
            file: Optional file to write to (defaults to stderr).
        """
        from usecli.cli.config.colors import COLOR
        console = _lazy_console()

        if file is None:
            file = sys.stderr

        console.print()

        error_prefix = (
            f"[bold black on {COLOR.ERROR}] ERROR [/bold black on {COLOR.ERROR}]"
        )
        error_msg = f"[bold {COLOR.ERROR}]{self.format_message()}[/bold {COLOR.ERROR}]"
        console.print(f"{error_prefix} {error_msg}")

        if self.ctx:
            help_text = _get_help_text_with_command_name(self.ctx)
            console.print(help_text)
