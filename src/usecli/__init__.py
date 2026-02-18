"""Usecli CLI main entry point."""

from __future__ import annotations

import sys

import click
import typer
from click.exceptions import BadParameter, ClickException, UsageError
from rich.console import Console
from typer.core import TyperGroup

from usecli.cli.core.exceptions import UsecliBadParameter, UsecliUsageError
from usecli.cli.core.ui.list import list_commands
from usecli.cli.services.command_service import CommandService

console = Console()


class PrefixMatchingGroup(TyperGroup):
    """Custom Typer group that supports prefix matching for commands.

    This allows users to type partial command names (e.g., 'he' for 'help').
    """

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Get a command by name, with prefix matching fallback.

        Args:
            ctx: The Click context.
            cmd_name: The command name or prefix to search for.

        Returns:
            The matching command, or None if not found.
        """
        rv = TyperGroup.get_command(self, ctx, cmd_name)
        if rv is not None:
            return rv

        matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]

        if not matches:
            return None

        if cmd_name in matches:
            return TyperGroup.get_command(self, ctx, cmd_name)

        return FilteredListCommand(cmd_name)

    def invoke(self, ctx: click.Context) -> None:
        """Invoke the group with custom error handling.

        Args:
            ctx: The Click context.

        Raises:
            SystemExit: On Click exceptions, after displaying styled errors.
        """
        try:
            return super().invoke(ctx)
        except BadParameter as e:
            styled_error = UsecliBadParameter(e.message, ctx=e.ctx, param=e.param)
            styled_error.show()
            sys.exit(styled_error.exit_code)
        except UsageError as e:
            styled_error = UsecliUsageError(e.message, ctx=e.ctx)
            styled_error.show()
            sys.exit(styled_error.exit_code)
        except ClickException as e:
            if hasattr(e, "show"):
                e.show()
            sys.exit(e.exit_code if hasattr(e, "exit_code") else 1)


class FilteredListCommand(click.Command):
    """Command that displays a filtered list of commands.

    This command is used when a user types a partial command name
    that matches multiple commands.
    """

    def __init__(self, prefix_filter: str) -> None:
        """Initialize the filtered list command.

        Args:
            prefix_filter: The prefix to filter commands by.
        """
        super().__init__(name="filtered-list")
        self.prefix_filter = prefix_filter

    def invoke(self, ctx: click.Context) -> None:
        """Invoke the command to display filtered commands.

        Args:
            ctx: The Click context.
        """
        list_commands(app, prefix_filter=self.prefix_filter)
        return None


app = typer.Typer(
    help="Usecli CLI - A tool for managing and utilizing specification files.",
    invoke_without_command=True,
    no_args_is_help=False,
    cls=PrefixMatchingGroup,
    pretty_exceptions_enable=False,  # Use custom error styling
)

service = CommandService(app)
service.load_commands()


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        None, "--version", "-v", help="Show the version and exit.", is_eager=True
    ),
    help: bool = typer.Option(None, "--help", "-h", is_eager=True),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Run in interactive mode", is_eager=True
    ),
) -> None:
    """Main callback for the CLI application.

    Handles version display, help display, and command listing when no
    subcommand is provided.

    Args:
        ctx: The Typer context.
        version: Flag to show version and exit.
        help: Flag to show help and exit.
    """
    if help:
        list_commands(app)
        raise typer.Exit()

    if version:
        console.print(
            f"[bold blue]CLI Version:[/bold blue] [green]{service.version}[/green]"
        )
        raise typer.Exit()

    if interactive:
        from usecli.cli.commands.defaults.base.internal.fzf_command import (
            run_interactive,
        )

        cmd_parts = [ctx.invoked_subcommand] if ctx.invoked_subcommand else None
        run_interactive(app, cmd_parts=cmd_parts)
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        prefix_filter: str | None = None
        if ctx.obj and isinstance(ctx.obj, dict):
            prefix_filter = ctx.obj.get("prefix_filter")
        list_commands(app, prefix_filter=prefix_filter)


def run_app() -> None:
    """Run the CLI application with custom error handling."""
    try:
        app()
    except BadParameter as e:
        styled_error = UsecliBadParameter(e.message, ctx=e.ctx, param=e.param)
        styled_error.show()
        sys.exit(styled_error.exit_code)
    except UsageError as e:
        styled_error = UsecliUsageError(e.message, ctx=e.ctx)
        styled_error.show()
        sys.exit(styled_error.exit_code)
    except ClickException as e:
        if hasattr(e, "show"):
            e.show()
        sys.exit(e.exit_code if hasattr(e, "exit_code") else 1)


if __name__ == "__main__":
    run_app()
