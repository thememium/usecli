"""Usecli CLI main entry point."""

from __future__ import annotations

import sys
from importlib import import_module
from typing import TYPE_CHECKING, Any, Optional, Sequence

if TYPE_CHECKING:
    import click
    import typer
    from rich.console import Console

    from usecli.cli.core.base_command import BaseCommand
    from usecli.menu import Menu
    from usecli.params import Argument, Option
    from usecli.ui import Confirm, Prompt

    console: Console

# Lazy module-level placeholders - these are populated on first access
_app: Any = None
_service: Any = None
_help_resolved: bool = False

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
    # Handle lazy exports
    export = _LAZY_EXPORTS.get(name)
    if export is not None:
        module_name, attr_name = export
        value = getattr(import_module(module_name), attr_name)
        globals()[name] = value
        return value

    # Handle CLI framework components - lazy initialization
    if name in ("app", "service", "BaseCommand", "colors", "theme"):
        _ensure_cli_initialized()
        return globals()[name]

    # Handle run_app callback
    if name == "run_app":
        _ensure_cli_initialized()
        _get_run_app_callback()
        return globals()[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _ensure_cli_initialized() -> None:
    """Lazily initialize the CLI framework components."""
    global _app, _service
    if _app is not None:
        return

    import click
    import typer
    from click.exceptions import BadParameter, ClickException, Exit, UsageError
    from typer.core import TyperGroup

    from usecli.cli.config.colors import COLOR
    from usecli.cli.core.base_command import BaseCommand
    from usecli.cli.services.command_service import CommandService

    # Store exceptions for error handling
    try:
        from typer._click.exceptions import BadParameter as TyperBadParameter  # type: ignore[import-untyped]
        from typer._click.exceptions import ClickException as TyperClickException  # type: ignore[import-untyped]
        from typer._click.exceptions import UsageError as TyperUsageError  # type: ignore[import-untyped]
    except ImportError:
        TyperBadParameter = BadParameter
        TyperClickException = ClickException
        TyperUsageError = UsageError

    # Store in globals for use by other functions
    globals()["_TyperBadParameter"] = TyperBadParameter
    globals()["_TyperClickException"] = TyperClickException
    globals()["_TyperUsageError"] = TyperUsageError
    globals()["_Exit"] = Exit
    globals()["_BadParameter"] = BadParameter
    globals()["_ClickException"] = ClickException
    globals()["_UsageError"] = UsageError
    globals()["_TyperGroup"] = TyperGroup

    # Create PrefixMatchingGroup now that TyperGroup is available
    class PrefixMatchingGroup(TyperGroup):
        """Custom Typer group that supports prefix matching for commands."""

        def get_command(self, ctx, cmd_name):
            """Get a command by name, with prefix matching fallback."""
            rv = TyperGroup.get_command(self, ctx, cmd_name)
            if rv is not None:
                return rv

            app = _get_app()
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

            return _FilteredListCommand(cmd_name)

        def main(
            self,
            args=None,
            prog_name=None,
            complete_var=None,
            standalone_mode=True,
            windows_expand_args=True,
            **extra,
        ):
            return super().main(
                args=args,
                prog_name=prog_name,
                complete_var=complete_var,
                standalone_mode=False,
                windows_expand_args=windows_expand_args,
                **extra,
            )

        def invoke(self, ctx):
            from click.exceptions import BadParameter, ClickException, Exit, UsageError

            try:
                return super().invoke(ctx)
            except Exit:
                sys.exit(0)
            except BadParameter as e:
                from usecli.cli.core.exceptions import UsecliBadParameter

                styled_error = UsecliBadParameter(e.message, ctx=e.ctx, param=e.param)
                styled_error.show()
                sys.exit(styled_error.exit_code)
            except UsageError as e:
                from usecli.cli.core.exceptions import UsecliUsageError

                styled_error = UsecliUsageError(e.message, ctx=e.ctx)
                styled_error.show()
                sys.exit(styled_error.exit_code)
            except ClickException as e:
                if hasattr(e, "show"):
                    e.show()
                sys.exit(e.exit_code if hasattr(e, "exit_code") else 1)

    globals()["PrefixMatchingGroup"] = PrefixMatchingGroup

    # Setup module aliasing
    colors = import_module("usecli.cli.config.colors")
    globals()["colors"] = colors
    globals()["theme"] = COLOR
    sys.modules.setdefault(__name__ + ".colors", colors)
    sys.modules.setdefault("colors", colors)

    # Create app and service
    _app = typer.Typer(
        help="Usecli CLI - An elegant CLI framework for Python",
        invoke_without_command=True,
        no_args_is_help=False,
        cls=PrefixMatchingGroup,
        pretty_exceptions_enable=False,
    )
    globals()["app"] = _app

    # Set BaseCommand BEFORE load_commands() since commands import it
    globals()["BaseCommand"] = BaseCommand

    _service = CommandService(_app)
    _service.load_commands()
    globals()["service"] = _service


def _get_app():
    _ensure_cli_initialized()
    return _app


def _get_service():
    _ensure_cli_initialized()
    return _service


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
    from usecli.shared.config.manager import get_config

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


def _get_group_alias_registry(app: Any) -> dict[str, list[str]]:
    registry = getattr(app, "_usecli_group_aliases", {})
    return registry if isinstance(registry, dict) else {}


def _build_alias_to_primary(alias_registry: dict[str, list[str]]) -> dict[str, str]:
    alias_to_primary: dict[str, str] = {}
    for primary, aliases in alias_registry.items():
        alias_to_primary[primary] = primary
        for alias in aliases:
            alias_to_primary[alias] = primary
    return alias_to_primary


# PrefixMatchingGroup is created lazily by _ensure_cli_initialized()
# to avoid importing typer at module level.
PrefixMatchingGroup = None


class _FilteredListCommand:
    """Command that displays a filtered list of commands."""

    def __init__(self, prefix_filter: str) -> None:
        self.prefix_filter = prefix_filter
        self.name = "filtered-list"

    def __call__(self, *args, **kwargs):
        from usecli.cli.core.ui.list import list_commands
        list_commands(_get_app(), prefix_filter=self.prefix_filter)


def _get_default_help() -> str:
    return "Usecli CLI - An elegant CLI framework for Python"


def _resolve_help():
    global _help_resolved
    if not _help_resolved:
        app = _get_app()
        app.info.help = _get_cli_help_text()
        _help_resolved = True


def _get_run_app_callback():
    """Get the run_app callback function."""
    if "run_app" in globals():
        return globals()["run_app"]

    import typer

    # Inject typer into module globals so annotation evaluation works
    # (required because `from __future__ import annotations` makes them strings)
    globals()["typer"] = typer

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
        _resolve_help()

        if help:
            from usecli.cli.core.ui.list import list_commands
            list_commands(_get_app())
            raise typer.Exit()

        if version:
            import shutil
            from usecli.shared.config.manager import get_config

            config = get_config()
            service = _get_service()
            command_path = shutil.which(sys.argv[0]) or sys.argv[0]
            _console().print(
                f"[bold {globals()['theme'].SECONDARY}]{config.get('title')} {service.version}[/bold {globals()['theme'].SECONDARY}] [{globals()['theme'].INFO}]({command_path})[/{globals()['theme'].INFO}]"
            )
            raise typer.Exit()

        interactive_requested = interactive or _is_interactive_flag_present()

        if interactive_requested:
            from usecli.cli.commands.defaults.base.internal.fzf_command import (
                run_interactive,
            )
            cmd_parts = [ctx.invoked_subcommand] if ctx.invoked_subcommand else None
            run_interactive(_get_app(), cmd_parts=cmd_parts)
            raise typer.Exit()

        if ctx.invoked_subcommand is None:
            prefix_filter: str | None = None
            if ctx.obj and isinstance(ctx.obj, dict):
                prefix_filter = ctx.obj.get("prefix_filter")
            from usecli.cli.core.ui.list import list_commands
            list_commands(_get_app(), prefix_filter=prefix_filter)

    globals()["run_app"] = run_app
    return run_app


def main() -> None:
    """Run the CLI application with custom error handling."""
    import typer
    from click.exceptions import BadParameter, ClickException, Exit, UsageError

    _ensure_cli_initialized()
    _resolve_help()

    from usecli.shared.config.manager import get_config

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

    # Setup the callback
    _get_run_app_callback()

    try:
        _get_app()()
    except Exit:
        sys.exit(0)
    except BadParameter as e:
        from usecli.cli.core.exceptions import UsecliBadParameter
        styled_error = UsecliBadParameter(e.message, ctx=e.ctx, param=e.param)
        styled_error.show()
        sys.exit(styled_error.exit_code)
    except UsageError as e:
        from usecli.cli.core.exceptions import UsecliUsageError
        styled_error = UsecliUsageError(e.message, ctx=e.ctx)
        styled_error.show()
        sys.exit(styled_error.exit_code)
    except ClickException as e:
        if hasattr(e, "show"):
            e.show()
        sys.exit(e.exit_code if hasattr(e, "exit_code") else 1)


if __name__ == "__main__":
    main()
