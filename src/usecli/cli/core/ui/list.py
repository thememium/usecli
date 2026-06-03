"""Command listing utilities for usecli CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

import click
import typer
from rich.console import Console

from usecli.cli.config.colors import COLOR
from usecli.cli.core.ui.title import (
    get_project_name,
    get_script_command_name,
    print_title,
)

if TYPE_CHECKING:
    pass

console = Console()

SPACER_LENGTH = 6


def _is_click_group(obj: object) -> bool:
    """Check if an object is a Click group (has subcommands).

    Works with both standard click.Group and Typer's vendored click
    (TyperGroup in typer>=0.26 no longer extends click.Group directly).
    """
    return isinstance(obj, click.Group) or (
        hasattr(obj, "commands") and isinstance(getattr(obj, "commands", None), dict)
    )


class CommandEntry(TypedDict):
    name: str
    display_name: str
    help: str
    aliases: list[str]


class CommandMeta(TypedDict):
    help: str
    aliases: list[str]


def list_commands(app: typer.Typer, prefix_filter: str | None = None) -> None:
    """List all available commands with optional filtering.

    Displays commands in a formatted list with sections for grouped commands
    (those with colons in their names).

    Args:
        app: The Typer application instance.
        prefix_filter: Optional prefix to filter commands by name.
    """
    project_name = get_project_name()
    print_title(title=project_name)

    click_group = typer.main.get_command(app)

    alias_registry = _get_alias_registry(app)
    alias_to_primary = _build_alias_to_primary(alias_registry)
    group_alias_registry = _get_group_alias_registry(app)
    group_alias_to_primary = _build_alias_to_primary(group_alias_registry)

    command_name = get_script_command_name(default="usecli")

    commands_by_name: dict[str, CommandMeta] = {}
    for command in app.registered_commands:
        callback = command.callback
        name = command.name or (
            getattr(callback, "__name__", "unknown") if callback else "unknown"
        )
        if name in alias_to_primary and alias_to_primary[name] != name:
            continue
        help_text = command.help or ""
        if name not in commands_by_name or (
            not commands_by_name[name]["help"] and help_text
        ):
            commands_by_name[name] = {
                "help": help_text,
                "aliases": alias_registry.get(name, list[str]()),
            }

    commands: list[CommandEntry] = []
    for name in commands_by_name:
        aliases = commands_by_name[name]["aliases"]
        command_entry: CommandEntry = {
            "name": name,
            "display_name": _format_display_name(name, aliases),
            "help": commands_by_name[name]["help"],
            "aliases": aliases,
        }
        commands.append(command_entry)
    commands.sort(key=lambda x: x["name"])

    groups: dict[str, str] = {}
    if _is_click_group(click_group):
        sub_commands: dict[str, object] = getattr(click_group, "commands", {})
        for cmd_name, cmd_obj in sub_commands.items():
            if _is_click_group(cmd_obj):
                if (
                    cmd_name in group_alias_to_primary
                    and group_alias_to_primary[cmd_name] != cmd_name
                ):
                    continue
                groups[cmd_name] = (
                    getattr(cmd_obj, "help", f"Commands for {cmd_name}")
                    or f"Commands for {cmd_name}"
                )

    option_flags = []
    display_params = _order_completion_params(click_group.params or [])
    if display_params:
        for param in display_params:
            flags = ", ".join(param.opts)
            if "--help" in flags:
                continue
            option_flags.append(flags)

    help_flags = "--help, -h"
    all_option_flags = [help_flags] + option_flags
    group_entries: list[CommandEntry] = []
    for group_name, group_help in groups.items():
        aliases = group_alias_registry.get(group_name, list[str]())
        group_entries.append(
            {
                "name": group_name,
                "display_name": _format_display_name(group_name, aliases),
                "help": group_help,
                "aliases": aliases,
            }
        )

    if prefix_filter:
        filtered = [
            c
            for c in commands
            if c["name"].startswith(prefix_filter)
            or any(alias.startswith(prefix_filter) for alias in c["aliases"])
        ]
        filtered_groups = [
            g
            for g in group_entries
            if g["name"].startswith(prefix_filter)
            or any(alias.startswith(prefix_filter) for alias in g["aliases"])
        ]
        if not filtered and not filtered_groups:
            console.print(f"  [dim]No commands found for '{prefix_filter}'[/dim]")
            console.print()
            return
        commands = filtered
        group_entries = filtered_groups

    all_display_names = [cmd["display_name"] for cmd in commands] + [
        entry["display_name"] for entry in group_entries
    ]
    all_labels = all_display_names + all_option_flags
    longest_label_length = max((len(label) for label in all_labels), default=0)

    console.print(f"[bold {COLOR.SECONDARY}]Usage:[/bold {COLOR.SECONDARY}]")
    console.print(f"  [{COLOR.PRIMARY}]{command_name} [OPTIONS] [ARGUMENTS]")
    console.print()

    console.print(f"[bold {COLOR.SECONDARY}]Options:")

    help_padding = " " * (longest_label_length - len(help_flags) + SPACER_LENGTH)
    console.print(
        f"  [{COLOR.OPTION}]{help_flags}[/{COLOR.OPTION}]{help_padding}Show this message and exit."
    )

    if display_params:
        for param in display_params:
            flags = ", ".join(param.opts)
            if "--help" in flags:
                continue
            description = _get_option_description(param)
            padding = " " * (longest_label_length - len(flags) + SPACER_LENGTH)
            console.print(
                f"  [{COLOR.OPTION}]{flags}[/{COLOR.OPTION}]{padding}{description}"
            )
    console.print()

    if not prefix_filter:
        console.print(f"[bold {COLOR.SECONDARY}]Available commands:")

    group_names = set(groups.keys())
    top_level: list[CommandEntry] = [
        c for c in commands if ":" not in c["name"] and c["name"] not in group_names
    ]
    with_colon: list[CommandEntry] = [c for c in commands if ":" in c["name"]]

    def print_command(cmd: CommandEntry) -> None:
        """Print a single command with proper formatting."""
        display_name = cmd["display_name"]
        padding = " " * (longest_label_length - len(display_name) + SPACER_LENGTH)
        console.print(
            f"  [{COLOR.COMMAND} not bold]{display_name}[/{COLOR.COMMAND} not bold]{padding}{cmd['help']}"
        )

    top_level.extend(group_entries)

    top_level.sort(key=lambda x: x["name"])

    if top_level:
        for cmd in top_level:
            print_command(cmd)
        console.print()

    sections: dict[str, list[CommandEntry]] = {}
    for cmd in with_colon:
        section_prefix = cmd["name"].split(":")[0]
        if section_prefix not in sections:
            sections[section_prefix] = []
        sections[section_prefix].append(cmd)

    for section_prefix, section_cmds in sections.items():
        console.print(f"[bold {COLOR.SECONDARY}]{section_prefix}:")
        for cmd in section_cmds:
            print_command(cmd)
        console.print()


def list_group_commands(group_app: typer.Typer, group_name: str) -> None:
    """List all commands within a specific command group.

    Displays commands in a formatted list for a nested command group,
    similar to how list_commands works for the main app.

    Args:
        group_app: The Typer sub-app for the command group.
        group_name: The name of the command group.
    """
    alias_registry = _get_alias_registry(group_app)
    alias_to_primary = _build_alias_to_primary(alias_registry)

    command_name = get_script_command_name(default="usecli")

    console.print(f"[bold {COLOR.SECONDARY}]Usage:[/bold {COLOR.SECONDARY}]")
    console.print(
        f"  [{COLOR.PRIMARY}]{command_name} {group_name} [COMMAND] [OPTIONS][/]"
    )
    console.print()
    commands_by_name: dict[str, CommandMeta] = {}
    for command in group_app.registered_commands:
        callback = command.callback
        name = command.name or (
            getattr(callback, "__name__", "unknown") if callback else "unknown"
        )
        if name in alias_to_primary and alias_to_primary[name] != name:
            continue
        help_text = command.help or ""
        if name not in commands_by_name or (
            not commands_by_name[name]["help"] and help_text
        ):
            commands_by_name[name] = {
                "help": help_text,
                "aliases": alias_registry.get(name, list[str]()),
            }

    commands: list[CommandEntry] = []
    for name in commands_by_name:
        aliases = commands_by_name[name]["aliases"]
        command_entry: CommandEntry = {
            "name": name,
            "display_name": _format_display_name(name, aliases),
            "help": commands_by_name[name]["help"],
            "aliases": aliases,
        }
        commands.append(command_entry)
    commands.sort(key=lambda x: x["name"])

    click_group = typer.main.get_command(group_app)
    option_flags = []
    display_params = _order_completion_params(click_group.params or [])
    if display_params:
        for param in display_params:
            flags = ", ".join(param.opts)
            if "--help" in flags:
                continue
            option_flags.append(flags)

    help_flags = "--help, -h"
    all_option_flags = [help_flags] + option_flags
    all_display_names = [cmd["display_name"] for cmd in commands]
    all_labels = all_display_names + all_option_flags
    longest_label_length = max((len(label) for label in all_labels), default=0)

    console.print(f"[bold {COLOR.SECONDARY}]Options:")
    help_padding = " " * (longest_label_length - len(help_flags) + SPACER_LENGTH)
    console.print(
        f"  [{COLOR.OPTION}]{help_flags}[/{COLOR.OPTION}]{help_padding}Show this message and exit."
    )

    if display_params:
        for param in display_params:
            flags = ", ".join(param.opts)
            if "--help" in flags:
                continue
            description = _get_option_description(param)
            padding = " " * (longest_label_length - len(flags) + SPACER_LENGTH)
            console.print(
                f"  [{COLOR.OPTION}]{flags}[/{COLOR.OPTION}]{padding}{description}"
            )
    console.print()

    console.print(f"[bold {COLOR.SECONDARY}]Available commands:")

    for cmd in commands:
        display_name = cmd["display_name"]
        padding = " " * (longest_label_length - len(display_name) + SPACER_LENGTH)
        console.print(
            f"  [{COLOR.COMMAND}]{display_name}[/{COLOR.COMMAND}]{padding}{cmd['help']}"
        )

    console.print()


def _get_alias_registry(app: typer.Typer) -> dict[str, list[str]]:
    registry = getattr(app, "_usecli_aliases", {})
    return registry if isinstance(registry, dict) else {}


def _get_group_alias_registry(app: typer.Typer) -> dict[str, list[str]]:
    registry = getattr(app, "_usecli_group_aliases", {})
    return registry if isinstance(registry, dict) else {}


def _get_option_description(param: click.Parameter) -> str:
    if "--show-completion" in param.opts:
        return "Show completion for the current shell."
    return getattr(param, "help", "") or ""


def _order_completion_params(
    params: list[click.Parameter],
) -> list[click.Parameter]:
    ordered = list(params)
    install_index = None
    show_index = None
    for index, param in enumerate(ordered):
        opts = set(param.opts)
        if "--install-completion" in opts:
            install_index = index
        if "--show-completion" in opts:
            show_index = index
    if install_index is None or show_index is None:
        return ordered
    if install_index < show_index:
        show_param = ordered.pop(show_index)
        ordered.insert(install_index, show_param)
        return ordered
    if show_index < install_index:
        install_param = ordered.pop(install_index)
        ordered.insert(show_index, install_param)
    return ordered


def _build_alias_to_primary(alias_registry: dict[str, list[str]]) -> dict[str, str]:
    alias_to_primary: dict[str, str] = {}
    for primary, aliases in alias_registry.items():
        alias_to_primary[primary] = primary
        for alias in aliases:
            alias_to_primary[alias] = primary
    return alias_to_primary


def _format_display_name(name: str, aliases: list[str]) -> str:
    if not aliases:
        return name
    return f"{name}, {', '.join(aliases)}"
