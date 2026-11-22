"""Usecli CLI main entry point."""

from __future__ import annotations

import sys
from importlib import import_module

# `typing` is already imported by click, so TYPE_CHECKING costs nothing extra.
# The block below gives type checkers concrete types for the lazy exports; the
# module `__getattr__` returns `Any` at runtime only.
from typing import TYPE_CHECKING

from click import Command as _ClickCommand

from usecli._rich_exports import RICH_EXPORT_NAMES

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    import typer

    from usecli.cli.config.colors import COLOR
    from usecli.cli.config.colors import COLOR as theme
    from usecli.cli.core.base_command import BaseCommand
    from usecli.cli.services.command_service import CommandService
    from usecli.menu import Menu
    from usecli.params import Argument, Option
    from usecli.progress import ProgressBar, Spinner
    from usecli.rich import (  # noqa: F401 - re-exported via __all__
        JSON,
        Align,
        Bar,
        BarColumn,
        Column,
        Columns,
        ConsoleOptions,
        ConsoleRenderable,
        Control,
        DownloadColumn,
        Group,
        Layout,
        LayoutRender,
        Live,
        Markdown,
        MofNCompleteColumn,
        Padding,
        Pretty,
        Progress,
        ProgressColumn,
        RenderableType,
        RenderHook,
        RichCast,
        Rule,
        Screen,
        Segment,
        Span,
        SpinnerColumn,
        Status,
        Style,
        StyleType,
        Syntax,
        TaskID,
        TaskProgressColumn,
        TextColumn,
        TextType,
        Theme,
        TimeElapsedColumn,
        TimeRemainingColumn,
        TotalFileSizeColumn,
        Traceback,
        TransferSpeedColumn,
        Tree,
        get_console,
        inspect,
        pprint,
        print_json,
        reconfigure,
        track,
    )
    from usecli.ui import Confirm, Console, Panel, Prompt, Table, Text, box

    # `print` must stay the builtin at runtime; this types only the re-export.
    print: Callable[..., None]

    console: Console
    app: typer.Typer
    service: CommandService

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
    "Spinner": ("usecli.progress", "Spinner"),
    "ProgressBar": ("usecli.progress", "ProgressBar"),
    "Table": ("usecli.ui", "Table"),
    "Text": ("usecli.ui", "Text"),
    "Panel": ("usecli.ui", "Panel"),
    "box": ("usecli.ui", "box"),
    "pyinstaller": ("usecli.bundler", "pyinstaller"),
    "run": ("usecli.entry", "run"),
    "prompt_skill_install": (
        "usecli.cli.commands.defaults.skill.install_command",
        "prompt_skill_install",
    ),
}

_RICH_EXPORTS = frozenset(RICH_EXPORT_NAMES)

# `print` must not be cached in this module's globals: the CLI code below calls
# the builtin, and a cached rich.print would silently replace it.
_UNCACHED_RICH_EXPORTS = frozenset({"print"})


def __getattr__(name: str) -> Any:
    # Handle lazy exports
    export = _LAZY_EXPORTS.get(name)
    if export is not None:
        module_name, attr_name = export
        value = getattr(import_module(module_name), attr_name)
        globals()[name] = value
        return value

    # Handle Rich components re-exported under the usecli namespace
    if name in _RICH_EXPORTS:
        value = getattr(import_module("usecli.rich"), name)
        if name not in _UNCACHED_RICH_EXPORTS:
            globals()[name] = value
        return value

    # Handle CLI framework components - lazy initialization
    if name in ("app", "service", "BaseCommand", "colors", "COLOR", "theme"):
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
    # Use BaseCommand as the guard - it's set last, so if it's present,
    # initialization completed successfully.
    if "BaseCommand" in globals():
        return

    global _app, _service

    import typer
    from click.exceptions import BadParameter, ClickException, Exit, UsageError
    from typer.core import TyperGroup

    from usecli.cli.config.colors import COLOR
    from usecli.cli.core.base_command import BaseCommand
    from usecli.cli.services.command_service import CommandService

    # Store exceptions for error handling
    # Typer vendors click internally and raises its own exception types.
    # We import them dynamically since typer._click has no type stubs.
    try:
        _typer_exceptions = import_module("typer._click.exceptions")
        TyperBadParameter: Any = _typer_exceptions.BadParameter
        TyperClickException: Any = _typer_exceptions.ClickException
        TyperUsageError: Any = _typer_exceptions.UsageError
    except (ImportError, AttributeError):
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
                return TyperGroup.get_command(
                    self, ctx, group_alias_to_primary[cmd_name]
                )

            matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]
            group_aliases = [
                alias for aliases in group_alias_registry.values() for alias in aliases
            ]
            matches.extend(
                [alias for alias in group_aliases if alias.startswith(cmd_name)]
            )
            matches = list(dict.fromkeys(matches))

            if not matches:
                return None

            if cmd_name in matches:
                if (  # pragma: no cover - unreachable duplicate of the branch above
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
            cli_args = list(args) if args is not None else sys.argv[1:]
            option_args = (
                cli_args[: cli_args.index("--")] if "--" in cli_args else cli_args
            )
            if "--json" not in option_args:
                return super().main(
                    args=args,
                    prog_name=prog_name,
                    complete_var=complete_var,
                    standalone_mode=False,
                    windows_expand_args=windows_expand_args,
                    **extra,
                )

            from contextlib import redirect_stdout

            from usecli.cli.core.runtime import (
                InvocationExit,
                JSONSerializationError,
                NonInteractiveError,
                error_document,
                execution_context,
                serialize_document,
                success_document,
            )

            original_stdout = sys.stdout
            _TyperBadParameter = globals()["_TyperBadParameter"]
            _TyperUsageError = globals()["_TyperUsageError"]
            _TyperClickException = globals()["_TyperClickException"]

            def write_document(document):
                original_stdout.write(serialize_document(document))
                original_stdout.flush()

            def fail(error_type: str, message: str, code: int):
                write_document(
                    error_document(
                        error_type=error_type,
                        message=message,
                        code=code,
                    )
                )
                raise SystemExit(code)

            with execution_context(json_mode=True):
                try:
                    with redirect_stdout(sys.stderr):
                        result = super().main(
                            args=args,
                            prog_name=prog_name,
                            complete_var=complete_var,
                            standalone_mode=False,
                            windows_expand_args=windows_expand_args,
                            **extra,
                        )
                    write_document(success_document(result))
                    return result
                except InvocationExit as error:
                    if error.code == 0:
                        write_document(success_document())
                        return None
                    fail("Exit", str(error), error.code)
                except Exit as error:
                    code = error.exit_code
                    if code == 0:
                        write_document(success_document())
                        return None
                    fail("Exit", f"Command exited with status {code}", code)
                except JSONSerializationError as error:
                    print(f"JSONSerializationError: {error}", file=sys.stderr)
                    fail("JSONSerializationError", str(error), 1)
                except NonInteractiveError as error:
                    print(f"NonInteractiveError: {error}", file=sys.stderr)
                    fail("NonInteractiveError", str(error), error.code)
                except (_TyperBadParameter, BadParameter) as error:
                    error.show(file=sys.stderr)
                    fail("BadParameter", error.format_message(), error.exit_code)
                except (_TyperUsageError, UsageError) as error:
                    error.show(file=sys.stderr)
                    fail("UsageError", error.format_message(), error.exit_code)
                except (_TyperClickException, ClickException) as error:
                    error.show(file=sys.stderr)
                    fail(
                        error.__class__.__name__,
                        error.format_message(),
                        error.exit_code,
                    )
                except SystemExit as error:
                    code = error.code if isinstance(error.code, int) else 1
                    if code == 0:
                        write_document(success_document())
                        return None
                    fail("Exit", f"Command exited with status {code}", code)
                except (
                    OSError,
                    RuntimeError,
                    ValueError,
                    TypeError,
                    AttributeError,
                    KeyError,
                ) as error:
                    print(
                        f"{error.__class__.__name__}: {error}",
                        file=sys.stderr,
                    )
                    fail(error.__class__.__name__, str(error), 1)

        def invoke(self, ctx):
            from click.exceptions import ClickException, Exit

            from usecli.cli.core.runtime import is_json_mode

            if is_json_mode():
                from usecli.cli.core.runtime import InvocationExit

                try:
                    return super().invoke(ctx)
                except Exit as error:
                    raise InvocationExit(error.exit_code) from error

            _TyperBadParameter = globals()["_TyperBadParameter"]
            _TyperUsageError = globals()["_TyperUsageError"]
            _TyperClickException = globals()["_TyperClickException"]

            try:
                return super().invoke(ctx)
            except Exit:
                sys.exit(0)
            except _TyperBadParameter as e:
                from usecli.cli.core.exceptions import UsecliBadParameter

                styled_error = UsecliBadParameter(
                    e.message,
                    ctx=e.ctx,
                    param=e.param,
                    formatted_message=e.format_message(),
                )
                styled_error.show()
                sys.exit(styled_error.exit_code)
            except _TyperUsageError as e:
                from usecli.cli.core.exceptions import UsecliUsageError

                styled_error = UsecliUsageError(e.message, ctx=e.ctx)
                styled_error.show()
                sys.exit(styled_error.exit_code)
            # UsecliError extends real-click ClickException, not the vendored
            # typer._click one — catch both, mirroring the JSON path.
            except (_TyperClickException, ClickException) as e:
                if hasattr(e, "show"):
                    e.show()
                sys.exit(e.exit_code if hasattr(e, "exit_code") else 1)

    globals()["PrefixMatchingGroup"] = PrefixMatchingGroup

    # Setup module aliasing
    colors = import_module("usecli.cli.config.colors")
    globals()["colors"] = colors
    globals()["COLOR"] = COLOR
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

    # Register the callback eagerly so --version/--help work
    # even when the app is accessed directly (e.g. smoke tests).
    _get_run_app_callback()


def _get_app():
    _ensure_cli_initialized()
    return _app


def _get_service():
    _ensure_cli_initialized()
    return _service


__all__ = [
    "COLOR",
    "Argument",
    "BaseCommand",
    "Confirm",
    "Console",
    "Menu",
    "Option",
    "Panel",
    "ProgressBar",
    "Prompt",
    "Spinner",
    "Table",
    "Text",
    "box",
    "colors",
    "console",
    "main",
    "prompt_skill_install",
    "pyinstaller",
    "run",
    "theme",
]

# Rich components come from usecli.rich; skip names already listed above.
__all__ += [name for name in RICH_EXPORT_NAMES if name not in __all__]


def _console():
    return __getattr__("console")


def _is_interactive_flag_present() -> bool:
    """Check for a global -i/--interactive flag before the command name.

    Flags placed after the command are handled by that command, which lets
    commands such as ``skill:install`` provide their own interactive prompts.
    ``usecli magic -i`` still reaches the same generic picker through the
    command's injected interactive option.

    Returns:
        True if -i or --interactive precedes the command in sys.argv.
    """
    for argument in sys.argv[1:]:
        if argument in {"-i", "--interactive"}:
            return True
        if not argument.startswith("-"):
            return False
    return False


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


class _FilteredListCommand(_ClickCommand):
    """Command that displays a filtered list of commands."""

    def __init__(self, prefix_filter: str) -> None:
        super().__init__(
            name="filtered-list",
            context_settings={},
            params=[],
            callback=None,
            help=None,
            epilog=None,
            short_help=None,
            no_args_is_help=False,
            hidden=False,
            deprecated=False,
        )
        self.prefix_filter = prefix_filter
        self.allow_extra_args = True
        self.allow_interspersed_args = True
        self.ignore_unknown_options = True

    def get_short_help_str(self, limit=45):
        return ""

    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: object | None = None,
        **extra: Any,
    ):
        from click import Context

        ctx = Context(self, info_name=info_name, **extra)
        return ctx

    def invoke(self, ctx):
        from usecli.cli.core.ui.list import list_commands

        return list_commands(_get_app(), prefix_filter=self.prefix_filter)

    def __call__(self, *args, **kwargs):
        from usecli.cli.core.ui.list import list_commands

        return list_commands(_get_app(), prefix_filter=self.prefix_filter)


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

    from usecli.shared.config.manager import get_config

    hide_skill_install = get_config().get_skill_install_mode() == "none"

    # Inject typer into module globals so annotation evaluation works
    # (required because `from __future__ import annotations` makes them strings)
    globals()["typer"] = typer

    @_app.callback()
    def run_app(
        ctx: typer.Context,
        version: bool = typer.Option(
            None, "--version", "-v", help="Show the version and exit.", is_eager=True
        ),
        help: bool = typer.Option(None, "--help", "-h", is_eager=True),
        interactive: bool = typer.Option(
            False, "--interactive", "-i", help="Run in interactive mode.", is_eager=True
        ),
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Emit one machine-readable JSON document.",
            is_eager=True,
        ),
        install_skills: bool = typer.Option(
            False,
            "--install-skills",
            help="Install the usecli skill for coding agents.",
            is_eager=True,
            hidden=hide_skill_install,
        ),
    ) -> object:
        _resolve_help()

        if help:
            from usecli.cli.core.ui.list import list_commands

            data = list_commands(_get_app())
            from usecli.cli.core.runtime import is_json_mode

            if is_json_mode():
                return data
            raise typer.Exit()

        if version:
            import shutil

            from usecli.cli.core.ui.title import get_project_name

            service = _get_service()
            command_path = shutil.which(sys.argv[0]) or sys.argv[0]
            _console().print(
                f"[bold {globals()['theme'].SECONDARY}]{get_project_name()} {service.version}[/bold {globals()['theme'].SECONDARY}] [{globals()['theme'].INFO}]({command_path})[/{globals()['theme'].INFO}]"
            )
            raise typer.Exit()

        if install_skills is True:
            from usecli.cli.commands.defaults.skill.install_command import (
                prompt_skill_install,
            )

            prompt_skill_install(_get_app())
            raise typer.Exit()

        interactive_requested = interactive or _is_interactive_flag_present()

        from usecli.cli.core.runtime import is_json_mode

        if interactive_requested and is_json_mode():
            from usecli.cli.core.runtime import NonInteractiveError

            raise NonInteractiveError("Interactive mode is unavailable in JSON mode")

        if interactive_requested:
            from usecli.cli.commands.defaults.base.internal.interactive_command import (
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

            return list_commands(_get_app(), prefix_filter=prefix_filter)

    globals()["run_app"] = run_app
    return run_app


def main() -> None:
    """Run the CLI application with custom error handling."""
    from click.exceptions import BadParameter, ClickException, Exit, UsageError

    _ensure_cli_initialized()
    _resolve_help()

    # Use typer's exception classes if available (they're subclasses of click's)
    # typer raises its own exceptions which may not match click's exactly
    _TyperBadParameter = globals().get("_TyperBadParameter", BadParameter)
    _TyperUsageError = globals().get("_TyperUsageError", UsageError)
    _TyperClickException = globals().get("_TyperClickException", ClickException)

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
    except _TyperBadParameter as e:
        from usecli.cli.core.exceptions import UsecliBadParameter

        styled_error = UsecliBadParameter(
            e.message,
            ctx=e.ctx,
            param=e.param,
            formatted_message=e.format_message(),
        )
        styled_error.show()
        sys.exit(styled_error.exit_code)
    except _TyperUsageError as e:
        from usecli.cli.core.exceptions import UsecliUsageError

        styled_error = UsecliUsageError(e.message, ctx=e.ctx)
        styled_error.show()
        sys.exit(styled_error.exit_code)
    except _TyperClickException as e:
        if hasattr(e, "show"):
            e.show()
        sys.exit(e.exit_code if hasattr(e, "exit_code") else 1)
    except (
        OSError,
        RuntimeError,
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
    ) as e:
        from usecli.cli.core.exceptions import UsecliUsageError

        styled_error = UsecliUsageError(str(e))
        styled_error.show()
        sys.exit(1)


if __name__ == "__main__":
    main()
