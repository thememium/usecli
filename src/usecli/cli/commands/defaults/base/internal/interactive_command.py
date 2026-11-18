"""Interactive command picker for the usecli CLI.

The picker is built on :mod:`simple_term_menu` — the same widget used elsewhere
in usecli — so ``--interactive`` works without an external fuzzy-finder binary.
It keeps the fzf feel: vim-style navigation (``j``/``k`` or arrows), ``/`` to
search and a styled cursor.
"""

from __future__ import annotations

import inspect
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import click
import typer
from rich.console import Console
from rich.prompt import Confirm, IntPrompt

from usecli.cli.config.colors import COLOR
from usecli.cli.core.error.handler import ErrorHandler
from usecli.cli.core.exceptions import UsecliError
from usecli.cli.core.ui import is_click_group
from usecli.cli.utils.interactive.terminal_menu import terminal_menu

if TYPE_CHECKING:
    from click.core import Command as ClickCommand

console = Console()

_STATUS_BAR = "↑↓/j/k move · / search · ctrl-u clear · ⏎ run · esc cancel"


def _get_required_arguments(command: ClickCommand) -> list[tuple[str, str, type]]:
    callback = command.callback
    if not callback:
        return []

    required: list[tuple[str, str, type]] = []
    sig = inspect.signature(callback)
    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue

        is_required = False

        if (
            param.default is inspect.Parameter.empty
            or hasattr(param.default, "default")
            and param.default.default is ...
        ):
            is_required = True

        if is_required:
            help_text = ""
            try:
                help_text = getattr(param.default, "help", "") or ""
            except AttributeError:  # pragma: no cover - getattr supplies a default
                pass

            param_type: type = param.annotation
            if param_type is inspect.Parameter.empty:
                param_type = str

            required.append((param_name, help_text, param_type))

    return required


def _get_optional_options(
    command: ClickCommand | typer.models.CommandInfo,
) -> list[tuple[str, str, str, type]]:
    click_command: click.Command | None = None
    if isinstance(command, click.Command):
        click_command = command
    elif isinstance(command, typer.models.CommandInfo):
        click_command = cast(
            click.Command,
            typer.main.get_command_from_info(
                command,
                pretty_exceptions_short=False,
                rich_markup_mode=None,
            ),
        )
    else:
        click_command = None

    if click_command is None or not click_command.params:
        return []

    options: list[tuple[str, str, str, type]] = []
    for param in click_command.params:
        if not isinstance(param, click.Option):
            continue

        option_names = ", ".join(param.opts)
        if "--help" in option_names:
            continue
        if "--interactive" in option_names or "-i" in option_names:
            continue
        if "--json" in option_names:
            continue

        help_text = param.help or ""
        param_name = param.name or ""

        if param.is_flag or isinstance(param.type, click.types.BoolParamType):
            param_type = bool
        elif isinstance(param.type, click.types.IntParamType):
            param_type = int
        else:
            param_type = str

        options.append((param_name, option_names, help_text, param_type))

    return options


def _clean_text(text: str) -> str:
    """Collapse whitespace so a description fits on one menu line."""
    return " ".join(text.split())


def _humanize_name(name: str) -> str:
    """Build a readable fallback description for a command with no help text."""
    words = name.replace(":", " ").replace("-", " ").replace("_", " ").split()
    return " ".join(words).capitalize()


def _fit(text: str, width: int) -> str:
    """Truncate text to ``width`` columns, adding an ellipsis when cut."""
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return "…"
    return text[: width - 1].rstrip() + "…"


def _menu_entry(name: str, description: str, name_width: int) -> str:
    """Render one two-column menu entry."""
    if description:
        display = f"{name:<{name_width}}  {description}".rstrip()
    else:
        display = name

    # simple-term-menu treats an unescaped ``|`` as a preview-argument
    # separator, so escape it to keep it visible in the row.
    return display.replace("|", "\\|")


def _run_command_menu(entries: list[str], *, title: str) -> str | None:
    """Show the interactive picker and return the selected entry.

    Returns ``None`` when the user cancels. Raises :class:`UsecliError` when
    there is no terminal to draw the menu on.
    """
    if not entries:
        return None

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise UsecliError(
            "Interactive mode requires a terminal",
            suggestion=(
                "Run the command with explicit arguments instead of using "
                "--interactive."
            ),
        )

    selection = terminal_menu(
        entries,
        title=title,
        search=True,
        search_key="/",
        vim_search=True,
        status_bar=_STATUS_BAR,
    )
    if not selection:
        return None

    return selection[0]


def _select_command(
    commands: list[dict[str, Any]],
    *,
    title: str,
) -> str | None:
    """Show a picker for ``commands`` and return the selected name."""
    if not commands:
        return None

    name_width = max(len(cmd["name"]) for cmd in commands)
    terminal_width = shutil.get_terminal_size((80, 24)).columns
    description_width = max(20, terminal_width - name_width - 6)

    entries: list[str] = []
    name_by_entry: dict[str, str] = {}
    for cmd in commands:
        description = _clean_text(cmd["help"]) or _humanize_name(cmd["name"])
        entry = _menu_entry(
            cmd["name"], _fit(description, description_width), name_width
        )
        entries.append(entry)
        name_by_entry[entry] = cmd["name"]

    selected = _run_command_menu(entries, title=title)
    if selected is None:
        return None
    return name_by_entry.get(selected)


def _resolve_group_alias(app: typer.Typer, group_name: str) -> str:
    registry = getattr(app, "_usecli_group_aliases", {})
    if not isinstance(registry, dict):
        return group_name
    for primary, aliases in registry.items():
        if group_name == primary:
            return primary
        if group_name in aliases:
            return primary
    return group_name


def _get_group_subcommands(
    app: typer.Typer,
    group_name: str,
) -> list[dict[str, Any]]:
    from usecli.cli.core.base_command import NestedCommandRegistry

    registry = NestedCommandRegistry()
    resolved_group = _resolve_group_alias(app, group_name)
    group_app = registry._groups.get(resolved_group)

    if not group_app:
        return []

    subcommands: list[dict[str, Any]] = []
    for command in group_app.registered_commands:
        name = command.name or "unknown"
        help_text = command.help or ""
        subcommands.append({"name": name, "help": help_text, "command": command})

    return subcommands


def run_interactive(
    app: typer.Typer,
    cmd_parts: list[str] | None = None,
    extra_args: list[str] | None = None,
) -> None:
    script_name = Path(sys.argv[0]).name or "usecli"
    commands: list[dict[str, Any]] = []

    for command in app.registered_commands:
        name = command.name or "unknown"
        help_text = command.help or ""
        commands.append({"name": name, "help": help_text, "command": command})

    if not commands:
        ErrorHandler.display_error("No commands available")
        raise typer.Exit(code=1)

    click_group = typer.main.get_command(app)
    groups: dict[str, str] = {}
    if is_click_group(click_group):
        sub_commands: dict[str, object] = getattr(click_group, "commands", {})
        for cmd_name, cmd_obj in sub_commands.items():
            if is_click_group(cmd_obj):
                groups[cmd_name] = (
                    getattr(cmd_obj, "help", f"Commands for {cmd_name}")
                    or f"Commands for {cmd_name}"
                )

    top_level = [
        c for c in commands if ":" not in c["name"] and c["name"] not in groups
    ]
    with_colon = [c for c in commands if ":" in c["name"]]

    top_level.sort(key=lambda x: x["name"])

    sections: dict[str, list[dict[str, Any]]] = {}
    for cmd in with_colon:
        section_prefix = cmd["name"].split(":")[0]
        if section_prefix not in sections:
            sections[section_prefix] = []
        sections[section_prefix].append(cmd)

    for section_cmds in sections.values():
        section_cmds.sort(key=lambda x: x["name"])
    sorted_sections = sorted(sections.items(), key=lambda x: x[0])

    for group_name, group_help in sorted(groups.items()):
        top_level.append({"name": group_name, "help": group_help, "is_group": True})

    ordered_commands = top_level + [
        cmd for _, section_cmds in sorted_sections for cmd in section_cmds
    ]

    cmd_name: str | None = None
    selected_cmd: dict[str, Any] | None = None

    if not cmd_parts:
        cmd_name = _select_command(
            ordered_commands,
            title=f"{script_name} » select a command",
        )
        if cmd_name is None:
            ErrorHandler.display_warning("No command selected")
            return

        selected_cmd = next(
            (c for c in ordered_commands if c["name"] == cmd_name), None
        )
        if not selected_cmd:
            ErrorHandler.display_error(f"Unknown command '{cmd_name}'")
            raise typer.Exit(code=1)
    else:
        cmd_name = cmd_parts[0]
        selected_cmd = next(
            (c for c in ordered_commands if c["name"] == cmd_name), None
        )
        if not selected_cmd:
            resolved_group = _resolve_group_alias(app, cmd_name)
            if resolved_group != cmd_name:
                cmd_name = resolved_group
                selected_cmd = next(
                    (c for c in ordered_commands if c["name"] == cmd_name), None
                )
        if not selected_cmd:
            ErrorHandler.display_error(f"Unknown command '{cmd_name}'")
            raise typer.Exit(code=1)

    if selected_cmd and selected_cmd.get("is_group"):
        subcommands = _get_group_subcommands(app, cmd_name)
        if not subcommands:
            ErrorHandler.display_error(f"No subcommands found for '{cmd_name}'")
            raise typer.Exit(code=1)

        subcommands.sort(key=lambda x: x["name"])

        sub_name: str | None = None
        if cmd_parts and len(cmd_parts) > 1:
            sub_name = cmd_parts[1]
        else:
            sub_name = _select_command(
                subcommands,
                title=f"{script_name} {cmd_name} » select a subcommand",
            )
            if sub_name is None:
                ErrorHandler.display_warning("No subcommand selected")
                return

        if not sub_name:
            ErrorHandler.display_error("Could not parse subcommand")
            raise typer.Exit(code=1)

        selected_sub = next((c for c in subcommands if c["name"] == sub_name), None)
        if not selected_sub:
            ErrorHandler.display_error(
                f"Unknown subcommand '{sub_name}' for '{cmd_name}'"
            )
            raise typer.Exit(code=1)

        cmd_name = f"{cmd_name} {sub_name}"
        selected_cmd = selected_sub
    elif cmd_parts and len(cmd_parts) > 1:
        ErrorHandler.display_error(f"Command '{cmd_name}' has no subcommands")
        raise typer.Exit(code=1)

    extra = " ".join(extra_args) if extra_args else ""

    required_args = (
        _get_required_arguments(selected_cmd["command"]) if selected_cmd else []
    )
    if required_args:
        help_result = subprocess.run(
            f"{script_name} {cmd_name} --help",
            shell=True,
            capture_output=True,
            text=True,
            env={**os.environ, "FORCE_COLOR": "1", "CLICOLOR_FORCE": "1"},
            check=False,
        )
        sys.stdout.write(help_result.stdout)

        console.rule(
            title=f"[bold {COLOR.PRIMARY}]── Enter required arguments for '{cmd_name}':[/bold {COLOR.PRIMARY}]",
            align="left",
            style=COLOR.PRIMARY,
        )
        console.print()

        arg_values: list[str] = []
        for arg_name, arg_help, arg_type in required_args:
            value: str | None = None

            if arg_type is bool:
                enabled = Confirm.ask(
                    f"[bold {COLOR.SECONDARY}]Enable '{arg_name}'?[/bold {COLOR.SECONDARY}]"
                    + (f" ({arg_help})" if arg_help else ""),
                    default=True,
                )
                value = "true" if enabled else "false"
                if enabled:
                    console.print(
                        f"[[bold {COLOR.SECONDARY}]✓[/bold {COLOR.SECONDARY}]] {arg_name} enabled"
                    )
                else:
                    console.print(
                        f"[[bold {COLOR.ERROR}]✗[/bold {COLOR.ERROR}]] {arg_name} disabled"
                    )
                console.print()
            elif arg_type is int:
                int_value = IntPrompt.ask(
                    f"[bold {COLOR.SECONDARY}]Enter value for '{arg_name}'[/bold {COLOR.SECONDARY}]"
                    + (f" ({arg_help})" if arg_help else "")
                )
                value = str(int_value)
            else:
                value = ""
                while not value:
                    prompt_text = f"Enter value for '{arg_name}'"
                    if arg_help:
                        prompt_text += f" ({arg_help})"
                    prompt_text += ":"
                    console.print(f"[bold {COLOR.SECONDARY}]{prompt_text}")
                    console.print(f"[bold {COLOR.SECONDARY}]└─> ", end="")

                    try:
                        user_input = input()
                        value = user_input.strip()
                    except EOFError:
                        value = ""
                    except KeyboardInterrupt:
                        ErrorHandler.display_warning("Cancelled by user")
                        raise typer.Exit(code=0)

                    if not value:
                        console.print(
                            f"[{COLOR.ERROR}]Value is required. Please enter a value.[/{COLOR.ERROR}]"
                        )

                if " " in value:
                    value = f'"{value}"'
                arg_values.append(value)

        if arg_values:
            extra = " ".join(arg_values)

    optional_options = (
        _get_optional_options(selected_cmd["command"]) if selected_cmd else []
    )
    if optional_options:
        console.print()
        console.print(
            f"[bold {COLOR.SECONDARY}]Select optional flags (space to select, enter to confirm):[/bold {COLOR.SECONDARY}]"
        )
        menu_options: list[str] = []
        for param_name, option_names, help_text, opt_type in optional_options:
            type_name = (
                opt_type.__name__ if hasattr(opt_type, "__name__") else str(opt_type)
            )
            display = option_names
            if type_name != "str":
                display += f" [{type_name}]"
            if help_text:
                display += f" - {help_text}"
            menu_options.append(display)

        selected_options = terminal_menu(
            menu_options,
            multi_select=True,
        )

        if not selected_options:
            ErrorHandler.display_warning("No optional flags selected")
        else:
            for opt in selected_options:
                console.print(
                    f"  [[bold {COLOR.PRIMARY}]*[/bold {COLOR.PRIMARY}]] {opt}"
                )
            console.print()

            option_values: list[str] = []
            for selected_option in selected_options:
                idx = menu_options.index(selected_option)
                (
                    _param_name,
                    option_names,
                    help_text,
                    opt_type,
                ) = optional_options[idx]
                first_flag = option_names.split(",")[0].strip()

                if opt_type is bool:
                    enabled = Confirm.ask(
                        f"[bold {COLOR.SECONDARY}]Enable {first_flag}?"
                        + (f" ({help_text})" if help_text else ""),
                        default=True,
                    )
                    if enabled:
                        option_values.append(first_flag)
                        console.print(
                            f"[[bold {COLOR.SECONDARY}]✓[/bold {COLOR.SECONDARY}]] {first_flag} enabled"
                        )
                    else:
                        console.print(
                            f"[[bold {COLOR.ERROR}]✗[/bold {COLOR.ERROR}]] {first_flag} disabled"
                        )
                    console.print()
                elif opt_type is int:
                    int_value = IntPrompt.ask(
                        f"[bold {COLOR.SECONDARY}]Value for {first_flag}"
                        + (f" ({help_text})" if help_text else "")
                    )
                    option_values.append(f"{first_flag} {int_value}")
                else:
                    opt_value = ""
                    while not opt_value:
                        prompt_text = f"[bold {COLOR.SECONDARY}]Value for {first_flag}"
                        if help_text:
                            prompt_text += f" ({help_text})"
                        prompt_text += ":"
                        console.print(prompt_text)
                        console.print(f"[bold {COLOR.SECONDARY}]└─> ", end="")
                        try:
                            opt_value = input().strip()
                        except KeyboardInterrupt:
                            ErrorHandler.display_warning("Cancelled by user")
                            raise typer.Exit(code=0)
                        if not opt_value:
                            console.print(
                                f"[{COLOR.ERROR}]Value is required. Please enter a value or press Ctrl+C to cancel.[/{COLOR.ERROR}]"
                            )
                    if " " in opt_value:
                        opt_value = f'"{opt_value}"'
                    option_values.append(f"{first_flag} {opt_value}")
            if option_values:
                extra = (
                    f"{extra} {' '.join(option_values)}"
                    if extra
                    else " ".join(option_values)
                )

    full_cmd = f"{script_name} {cmd_name}{' ' + extra if extra else ''}"

    console.print()
    console.rule(
        f"[bold {COLOR.PRIMARY}]── Running Command:",
        align="left",
        style=COLOR.PRIMARY,
    )
    console.print()
    console.print(f"[bold {COLOR.WARNING}]{full_cmd}")
    console.print()

    subprocess.run(full_cmd, shell=True, check=False)
