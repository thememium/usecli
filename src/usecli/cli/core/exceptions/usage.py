"""Usage and parameter errors for usecli CLI."""

from __future__ import annotations

import sys
from typing import IO

from click.core import Context as ClickContext
from click.exceptions import BadParameter, Exit, UsageError
from rich.console import Console

from usecli.cli.config.colors import COLOR
from usecli.cli.core.ui.title import get_script_command_name

console = Console(stderr=True)


def _get_help_text_with_command_name(ctx: ClickContext) -> str:
    # ctx.get_help() delegates to ctx.command.get_help(ctx). Commands built
    # from BaseCommand use CustomHelpCommand, whose get_help() prints the
    # help directly and raises Exit(0) instead of returning a string (see
    # base_command.py) so that a bare `--help` exits cleanly. That contract
    # break means this call can raise instead of returning text whenever
    # ctx.command is a CustomHelpCommand (i.e. any real subcommand). Left
    # uncaught, the Exit(0) propagates out of show() and is interpreted by
    # click/typer as "the command exited 0", clobbering the exit code this
    # usage error was about to set. The help has already been printed as a
    # side effect by that point, so it's safe to treat this as "no
    # additional help text to append" and let the caller continue.
    command_name = get_script_command_name(default=getattr(ctx, "info_name", None))
    if not command_name:
        try:
            return ctx.get_help()
        except Exit:
            return ""

    original_info_name = getattr(ctx, "info_name", None)
    try:
        ctx.info_name = command_name
        return ctx.get_help()
    except Exit:
        return ""
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
