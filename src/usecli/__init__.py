"""Usecli CLI main entry point."""

from __future__ import annotations

import sys
from importlib import import_module
from typing import TYPE_CHECKING, Any, Optional, Sequence

import click
import typer
from click.exceptions import BadParameter, ClickException, Exit, UsageError
from typer.core import TyperGroup

if TYPE_CHECKING:
    from rich.console import Console

    from usecli.menu import Menu
    from usecli.params import Argument, Option
    from usecli.ui import Confirm, Prompt

    console: Console

try:
    from typer._click.exceptions import BadParameter as TyperBadParameter  # type: ignore[import-untyped]
    from typer._click.exceptions import ClickException as TyperClickException  # type: ignore[import-untyped]
    from typer._click.exceptions import UsageError as TyperUsageError  # type: ignore[import-untyped]
except ImportError:
    TyperBadParameter = BadParameter
    TyperClickException = ClickException
    TyperUsageError = UsageError

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.cli.services.command_service import CommandService
from usecli.shared.config.manager import get_config

colors = import_module("usecli.cli.config.colors")
theme = COLOR

sys.modules.setdefault(__name__ + ".colors", colors)
sys.modules.setdefault("colors", colors)

_LAZY_EXPORTS = {
    "Menu": ("usecli.menu", "Menu"),
    "Argument": ("usecli.params", "Argument"),
    "Option": ("usecli.params", "Option"),
    "Prompt": ("usecli.ui", "Prompt"),
    "Confirm": ("usecli.ui", "Confirm"),
    "Console": ("usecli.ui", "Console"),
    "console": ("usecli.ui", "console"),
}


def __getattr__(name: str) -> Any:
    export = _LAZY_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = export
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


__all__ = [
    "BaseCommand",
    "console",
    "Console",
    "main",
    "Menu",
    "Argument",
    "Option",
    "Prompt",
    "Confirm",
    "colors",
    "theme",
]


def _console():
    return __getattr__("console")


def _is_interactive_flag_present() -> bool:
    """Check if -i/--interactive flag is present in sys.argv.

    This allows the interactive flag to work regardless of position,
    e.g., both 'usecli -i magic' and 'usecli magic -i' will work.

    Returns:
        True if -i or --interactive is found in sys.argv, False otherwise.
    """
    return "-i" in sys.argv or "--interactive" in sys.argv


def _get_cli_help_text() -> str:
    fallback = "Usecli CLI - An elegant CLI framework for Python"
    fallback_description = "An elegant CLI framework for Python"
    config = get_config()

    description = config.get("description")
    has_description = (
        config.has_key("description")
        and isinstance(description, str)
        and description.strip()
    )

    title = config.get("title")
    has_title = config.has_key("title") and isinstance(title, str) and title.strip()

    command_name = config.get("command_name")
    has_command_name = (
        config.has_key("command_name")
        and isinstance(command_name, str)
        and command_name.strip()
    )

    if not has_description and not has_title and not has_command_name:
        return fallback

    display_name = (
        title.strip()
        if has_title
        else command_name.strip()
        if has_command_name
        else "Usecli CLI"
    )
    display_description = (
        description.strip() if has_description else fallback_description
    )
    return f"{display_name} - {display_description}"


def _get_group_alias_registry(app: typer.Typer) -> dict[str, list[str]]:
    registry = getattr(app, "_usecli_group_aliases", {})
    return registry if isinstance(registry, dict) else {}


def _build_alias_to_primary(alias_registry: dict[str, list[str]]) -> dict[str, str]:
    alias_to_primary: dict[str, str] = {}
    for primary, aliases in alias_registry.items():
        alias_to_primary[primary] = primary
        for alias in aliases:
            alias_to_primary[alias] = primary
    return alias_to_primary


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

        group_alias_registry = _get_group_alias_registry(app)
        group_alias_to_primary = _build_alias_to_primary(group_alias_registry)

        if (
            cmd_name in group_alias_to_primary
            and group_alias_to_primary[cmd_name] != cmd_name
        ):
            return TyperGroup.get_command(self, ctx, group_alias_to_primary[cmd_name])

        matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]
        group_aliases = [
            alias for aliases in group_alias_registry.values() for alias in aliases
        ]
        matches.extend([alias for alias in group_aliases if alias.startswith(cmd_name)])
        matches = list(dict.fromkeys(matches))

        if not matches:
            return None

        if cmd_name in matches:
            if (
                cmd_name in group_alias_to_primary
                and group_alias_to_primary[cmd_name] != cmd_name
            ):
                return TyperGroup.get_command(
                    self, ctx, group_alias_to_primary[cmd_name]
                )
            return TyperGroup.get_command(self, ctx, cmd_name)

        return FilteredListCommand(cmd_name)

    def main(
        self,
        args: Optional[Sequence[str]] = None,
        prog_name: Optional[str] = None,
        complete_var: Optional[str] = None,
        standalone_mode: bool = True,
        windows_expand_args: bool = True,
        **extra: Any,
    ) -> Any:
        """Override main to disable standalone mode.

        Click's default standalone_mode=True catches ClickException
        internally and calls sys.exit(), preventing our custom error
        handlers from running. Setting standalone_mode=False lets
        exceptions propagate to our styled error handlers in invoke().
        """
        return super().main(
            args=args,
            prog_name=prog_name,
            complete_var=complete_var,
            standalone_mode=False,
            windows_expand_args=windows_expand_args,
            **extra,
        )

    def invoke(self, ctx: click.Context) -> None:
        """Invoke the group with custom error handling.

        Args:
            ctx: The Click context.

        Raises:
            SystemExit: On Click exceptions, after displaying styled errors.
        """
        try:
            return super().invoke(ctx)
        except Exit:
            sys.exit(0)
        except (BadParameter, TyperBadParameter) as e:
            from usecli.cli.core.exceptions import UsecliBadParameter

            styled_error = UsecliBadParameter(e.message, ctx=e.ctx, param=e.param)
            styled_error.show()
            sys.exit(styled_error.exit_code)
        except (UsageError, TyperUsageError) as e:
            from usecli.cli.core.exceptions import UsecliUsageError

            styled_error = UsecliUsageError(e.message, ctx=e.ctx)
            styled_error.show()
            sys.exit(styled_error.exit_code)
        except (ClickException, TyperClickException) as e:
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
        from usecli.cli.core.ui.list import list_commands

        list_commands(app, prefix_filter=self.prefix_filter)
        return None


def _get_default_help() -> str:
    return "Usecli CLI - An elegant CLI framework for Python"


app = typer.Typer(
    help=_get_default_help(),
    invoke_without_command=True,
    no_args_is_help=False,
    cls=PrefixMatchingGroup,
    pretty_exceptions_enable=False,  # Use custom error styling
)

_help_resolved = False


def _resolve_help():
    global _help_resolved
    if not _help_resolved:
        app.info.help = _get_cli_help_text()
        _help_resolved = True


service = CommandService(app)
service.load_commands()


@app.callback()
def run_app(
    ctx: typer.Context,
    version: bool = typer.Option(
        None, "--version", "-v", help="Show the version and exit.", is_eager=True
    ),
    help: bool = typer.Option(None, "--help", "-h", is_eager=True),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Run in interactive mode.", is_eager=True
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
    _resolve_help()

    if help:
        from usecli.cli.core.ui.list import list_commands

        list_commands(app)
        raise typer.Exit()

    if version:
        import shutil

        config = get_config()
        command_path = shutil.which(sys.argv[0]) or sys.argv[0]
        _console().print(
            f"[bold {theme.SECONDARY}]{config.get('title')} {service.version}[/bold {theme.SECONDARY}] [{theme.INFO}]({command_path})[/{theme.INFO}]"
        )
        raise typer.Exit()

    interactive_requested = interactive or _is_interactive_flag_present()

    if interactive_requested:
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
        from usecli.cli.core.ui.list import list_commands

        list_commands(app, prefix_filter=prefix_filter)


def main() -> None:
    """Run the CLI application with custom error handling."""
    _resolve_help()
    config = get_config()
    command_name = config._get_command_name()
    if command_name == "usecli" and not config.is_usecli_direct_dependency():
        _console().print(
            "[bold red]Error:[/bold red] usecli is not a direct dependency of this project."
        )
        _console().print(
            "Add it to your [cyan]pyproject.toml[/cyan] dependencies or dependency-groups."
        )
        sys.exit(1)

    try:
        app()
    except Exit:
        sys.exit(0)
    except (BadParameter, TyperBadParameter) as e:
        from usecli.cli.core.exceptions import UsecliBadParameter

        styled_error = UsecliBadParameter(e.message, ctx=e.ctx, param=e.param)
        styled_error.show()
        sys.exit(styled_error.exit_code)
    except (UsageError, TyperUsageError) as e:
        from usecli.cli.core.exceptions import UsecliUsageError

        styled_error = UsecliUsageError(e.message, ctx=e.ctx)
        styled_error.show()
        sys.exit(styled_error.exit_code)
    except (ClickException, TyperClickException) as e:
        if hasattr(e, "show"):
            e.show()
        sys.exit(e.exit_code if hasattr(e, "exit_code") else 1)


if __name__ == "__main__":
    main()
