"""Fzf command for interactive command finder."""

from __future__ import annotations

import inspect
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
import typer
from rich.console import Console
from rich.prompt import Confirm, IntPrompt

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.cli.core.error.handler import ErrorHandler
from usecli.cli.core.exceptions import UsecliError
from usecli.cli.utils.interactive.terminal_menu import terminal_menu

if TYPE_CHECKING:
    from click.core import Command as ClickCommand

console = Console()


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

        if param.default is inspect.Parameter.empty:
            is_required = True
        elif hasattr(param.default, "default") and param.default.default is ...:
            is_required = True

        if is_required:
            help_text = ""
            try:
                help_text = getattr(param.default, "help", "") or ""
            except AttributeError:
                pass

            param_type: type = param.annotation
            if param_type is inspect.Parameter.empty:
                param_type = str

            required.append((param_name, help_text, param_type))

    return required


def _get_optional_options(
    command: ClickCommand | typer.models.CommandInfo,
) -> list[tuple[str, str, str, type]]:
    click_command: click.Command | None
    if isinstance(command, click.Command):
        click_command = command
    elif isinstance(command, typer.models.CommandInfo):
        click_command = typer.main.get_command_from_info(
            command,
            pretty_exceptions_short=False,
            rich_markup_mode=None,
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


def _run_fzf_menu(
    options: list[str],
    prompt: str = "usecli » ",
) -> str | None:
    if not sys.stdin.isatty() or not sys.stdout.isatty() or not shutil.which("fzf"):
        selection = terminal_menu(options, title=prompt.strip())
        return selection[0] if selection else None

    input_data = "\n".join(options)

    fzf_args = [
        "fzf",
        "--ansi",
        f"--prompt={prompt}",
        f"--color=prompt:{COLOR.SECONDARY}",
        "--layout=reverse",
        "--height=~40%",
        "--border",
        f"--color=border:{COLOR.PRIMARY}",
        "--bind=ctrl-d:half-page-down",
        "--bind=ctrl-u:half-page-up",
    ]

    try:
        result = subprocess.run(
            fzf_args,
            input=input_data,
            capture_output=True,
            text=True,
        )

        if result.returncode == 130 or not result.stdout.strip():
            return None

        if result.returncode != 0:
            ErrorHandler.display_error(
                f"fzf error: {result.stderr}",
                suggestion="Check fzf installation and try again",
            )
            raise typer.Exit(code=1)

        return result.stdout.strip()

    except FileNotFoundError:
        raise UsecliError(
            "fzf is not installed",
            suggestion="Install fzf: https://github.com/junegunn/fzf#installation",
        )


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
    if isinstance(click_group, click.Group):
        for cmd_name, cmd_obj in click_group.commands.items():
            if isinstance(cmd_obj, click.Group):
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

    for group_name, group_help in groups.items():
        top_level.append({"name": group_name, "help": group_help, "is_group": True})

    ordered_commands = top_level + [
        cmd for _, section_cmds in sorted_sections for cmd in section_cmds
    ]
    max_name_len = max(len(cmd["name"]) for cmd in ordered_commands)

    def build_option_line(cmd: dict[str, Any], padding_len: int) -> str:
        padding = " " * padding_len
        return (
            f"{COLOR.ANSI.PRIMARY}{cmd['name']}{COLOR.ANSI.RESET}"
            f"{padding}{COLOR.ANSI.FOREGROUND_MUTED}{cmd['help']}{COLOR.ANSI.RESET}"
        )

    cmd_name: str | None = None
    selected_cmd: dict[str, Any] | None = None

    if not cmd_parts:
        options: list[str] = []
        for cmd in ordered_commands:
            padding_len = max_name_len - len(cmd["name"]) + 4
            options.append(build_option_line(cmd, padding_len))

        selection = _run_fzf_menu(options, prompt=f"{script_name} » ")
        if selection is None:
            ErrorHandler.display_warning("No command selected")
            return

        cmd_name = selection.split()[0] if selection else None
        if not cmd_name:
            ErrorHandler.display_error("Could not parse command")
            raise typer.Exit(code=1)

        selected_cmd = next(
            (c for c in ordered_commands if c["name"] == cmd_name), None
        )
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
        max_sub_name_len = max(len(cmd["name"]) for cmd in subcommands)

        sub_name: str | None = None
        if cmd_parts and len(cmd_parts) > 1:
            sub_name = cmd_parts[1]
        else:
            sub_options: list[str] = []
            for cmd in subcommands:
                padding_len = max_sub_name_len - len(cmd["name"]) + 4
                sub_options.append(build_option_line(cmd, padding_len))

            sub_selection = _run_fzf_menu(
                sub_options, prompt=f"{script_name} {cmd_name} » "
            )
            if sub_selection is None:
                ErrorHandler.display_warning("No subcommand selected")
                return
            sub_name = sub_selection.split()[0] if sub_selection else None

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
                    param_name,
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

    subprocess.run(full_cmd, shell=True)

    try:
        pass
    except KeyboardInterrupt:
        ErrorHandler.display_warning("Cancelled by user")
        raise typer.Exit(code=0)


class FzfCommand(BaseCommand):
    """Interactive command finder using fzf."""

    def signature(self) -> str:
        """Return the command signature."""
        return "fzf"

    def description(self) -> str:
        """Return the command description."""
        return "Interactive command finder using fzf"

    def handle(
        self,
        extra_args: list[str] = typer.Argument(
            None, help="Additional arguments to pass to the selected command"
        ),
    ) -> None:
        """Handle the fzf command execution.

        Args:
            extra_args: Additional arguments to pass to the selected command.
        """
        run_interactive(self.app, extra_args=extra_args)
