"""Install bundled usecli skills for AI coding agents."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, Any

import typer
from jinja2 import Template
from rich.console import Console

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.cli.core.exceptions import UsecliBadParameter
from usecli.cli.core.ui.list import collect_commands_data
from usecli.cli.core.ui.title import get_script_command_name
from usecli.shared.config.globals import TEMPLATES_DIR
from usecli.shared.config.manager import find_project_root, get_config, reset_config
from usecli.skills import (
    AGENT_TARGETS,
    InstallResult,
    Skill,
    SkillError,
    discover_skills,
    install_skill,
    install_skills,
    resolve_agents,
    select_skills,
)

console = Console()

FRAMEWORK_SKILL_NAME = "usecli"
FRAMEWORK_SKILL_DESCRIPTION = (
    "Build, extend, and operate usecli-based Python CLIs. Use when a repository "
    "depends on usecli, contains a usecli.config.toml, or the user asks to add, "
    "change, or debug usecli commands, themes, JSON output, or packaging."
)

_STATUS_COLORS = {
    "installed": COLOR.SUCCESS,
    "updated": COLOR.SUCCESS,
    "adopted": COLOR.SUCCESS,
    "already_installed": COLOR.FOREGROUND_MUTED,
    "user_modified": COLOR.WARNING,
    "overwritten": COLOR.WARNING,
}


def _project_root() -> Path:
    return find_project_root(Path.cwd()) or Path.cwd().resolve()


def _framework_version() -> str:
    try:
        return version("usecli")
    except PackageNotFoundError:
        return "0.0.0"


def _param_label(param: Any) -> str | None:
    """Human-readable flag/argument label for a click parameter."""
    if getattr(param, "param_type_name", "option") == "argument":
        name = getattr(param, "name", None)
        return f"<{name.upper()}>" if name else "<ARG>"

    flags = [*getattr(param, "opts", []), *getattr(param, "secondary_opts", [])]
    if not flags:
        return None
    return ", ".join(flags)


def _is_global_option(param: Any) -> bool:
    flags = set(getattr(param, "opts", [])) | set(getattr(param, "secondary_opts", []))
    return bool(
        flags
        & {
            "--help",
            "-h",
            "--interactive",
            "-i",
            "--json",
            "--show-completion",
            "--install-completion",
        }
    )


def _describe_param(param: Any) -> dict[str, str] | None:
    if _is_global_option(param):
        return None
    label = _param_label(param)
    if not label:
        return None
    return {"label": label, "help": getattr(param, "help", None) or ""}


def _describe_command(
    name: str,
    command: Any | None,
    aliases: list[str],
) -> dict[str, Any]:
    params: list[dict[str, str]] = []
    for param in getattr(command, "params", []) or []:
        described = _describe_param(param)
        if described is not None:
            params.append(described)

    help_text = ""
    if command is not None:
        help_text = getattr(command, "help", None) or getattr(
            command, "short_help", None
        )
    if help_text:
        help_text = " ".join(str(help_text).split())

    return {
        "name": name,
        "help": help_text,
        "aliases": aliases,
        "params": params,
    }


def collect_skill_commands(app: typer.Typer) -> list[dict[str, Any]]:
    """Describe every registered command for the generated skill."""
    data = collect_commands_data(app)
    click_root = typer.main.get_command(app)
    root_commands = getattr(click_root, "commands", {}) or {}

    commands: list[dict[str, Any]] = []
    for entry in data["commands"]:
        commands.append(
            _describe_command(
                entry["name"],
                root_commands.get(entry["name"]),
                entry["aliases"],
            )
        )

    for entry in data["groups"]:
        group_name = entry["name"]
        group_command = root_commands.get(group_name)
        commands.append(_describe_command(group_name, group_command, entry["aliases"]))
        subcommands = getattr(group_command, "commands", {}) or {}
        for sub_name, sub_command in subcommands.items():
            commands.append(
                _describe_command(f"{group_name} {sub_name}", sub_command, [])
            )

    commands.sort(key=lambda command: command["name"])
    return commands


def render_skill(app: typer.Typer, *, command_name: str) -> str:
    """Render the framework skill for the current app and project."""
    template = Template(
        (TEMPLATES_DIR / "skill.md.j2").read_text(encoding="utf-8"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return template.render(
        command_name=command_name,
        version=_framework_version(),
        commands=collect_skill_commands(app),
    )


def _framework_skill(app: typer.Typer) -> Skill:
    command_name = get_script_command_name(default="usecli") or "usecli"
    return Skill(
        name=FRAMEWORK_SKILL_NAME,
        description=FRAMEWORK_SKILL_DESCRIPTION,
        content=render_skill(app, command_name=command_name),
    )


def _discover_project_skills() -> list[Skill]:
    config = get_config()
    current_root = _project_root()
    if config.get_project_root().resolve() != current_root:
        reset_config()
        config = get_config()
    return discover_skills(config.get_project_skills_dir())


def _select_skills(app: typer.Typer, names: list[str] | None) -> list[Skill]:
    project_skills = _discover_project_skills()
    has_framework_override = any(
        skill.name == FRAMEWORK_SKILL_NAME for skill in project_skills
    )
    available = (
        project_skills
        if has_framework_override
        else [*project_skills, _framework_skill(app)]
    )
    return select_skills(available, names)


def _status_color(status: str) -> str:
    if status.startswith("error:"):
        return COLOR.ERROR
    return _STATUS_COLORS.get(status, COLOR.FOREGROUND)


def _list_data(
    skills: list[Skill],
    agents: list[str],
    *,
    scope: str,
    project_root: Path,
) -> dict[str, Any]:
    return {
        "scope": scope,
        "skills": [
            {
                "name": skill.name,
                "description": skill.description,
                "source": skill.source,
            }
            for skill in skills
        ],
        "agents": [
            {
                "name": agent,
                "path": str(
                    AGENT_TARGETS[agent].base(
                        scope,
                        project_root=project_root,
                    )
                    / "skills"
                ),
            }
            for agent in agents
        ],
    }


def _print_list(data: dict[str, Any]) -> None:
    console.print()
    console.print(f"[bold {COLOR.PRIMARY}]Bundled skills[/bold {COLOR.PRIMARY}]")
    for skill in data["skills"]:
        console.print(
            f"  [{COLOR.COMMAND}]{skill['name']}[/{COLOR.COMMAND}]  "
            f"{skill['description']}"
        )
    console.print()
    console.print(f"[bold {COLOR.PRIMARY}]Agent targets[/bold {COLOR.PRIMARY}]")
    for agent in data["agents"]:
        console.print(f"  {agent['name']:<12} {agent['path']}")
    console.print()


def _print_results(data: dict[str, Any]) -> None:
    console.print()
    for result in data["installed"]:
        console.print(
            f"  [{_status_color(result['status'])}]{result['status']:<16}"
            f"[/{_status_color(result['status'])}] "
            f"{result['skill']} [{COLOR.FOREGROUND_MUTED}]->[/] "
            f"{result['agent']} {result['path']}"
        )

    if any(result["status"] == "user_modified" for result in data["installed"]):
        console.print()
        console.print(
            f"[{COLOR.WARNING}]Some skills were left untouched because they "
            f"were edited locally. Re-run with --force to overwrite them."
            f"[/{COLOR.WARNING}]"
        )
    if data["errors"]:
        console.print()
        for error in data["errors"]:
            console.print(f"[{COLOR.ERROR}]{error}[/{COLOR.ERROR}]")
    console.print()


class InstallSkillCommand(BaseCommand):
    """Install bundled skills for AI coding agents."""

    def signature(self) -> str:
        return "skill:install"

    def description(self) -> str:
        return "Install bundled skills for coding agents"

    def handle(
        self,
        global_: Annotated[
            bool,
            typer.Option(
                "--global",
                "-g",
                help="Install for every project instead of the current project.",
            ),
        ] = False,
        agent: Annotated[
            list[str] | None,
            typer.Option(
                "--agent",
                "-a",
                help=(
                    "Agent target: all, claude, codex, cursor, opencode, pi, "
                    "prime-agent, omp, or agents. Repeat or comma-separate."
                ),
            ),
        ] = None,
        skill: Annotated[
            list[str] | None,
            typer.Option(
                "--skill",
                "-s",
                help="Install only these skills. Repeat or comma-separate.",
            ),
        ] = None,
        path: Annotated[
            Path | None,
            typer.Option(
                "--path",
                help="Install one selected skill into this exact directory.",
            ),
        ] = None,
        force: Annotated[
            bool,
            typer.Option(
                "--force",
                "-f",
                help="Overwrite skills that have local edits.",
            ),
        ] = False,
        list_: Annotated[
            bool,
            typer.Option(
                "--list",
                "-l",
                help="List bundled skills and agent targets without installing.",
            ),
        ] = False,
    ) -> dict[str, Any]:
        if global_ and path is not None:
            raise UsecliBadParameter("--global and --path cannot be used together")
        if path is not None and agent:
            raise UsecliBadParameter("--path and --agent cannot be used together")

        project_root = _project_root()
        scope = "global" if global_ else "project"

        try:
            skills = _select_skills(self.app, skill)
            agents = resolve_agents(agent)
        except SkillError as error:
            raise UsecliBadParameter(str(error)) from error

        if path is not None and not skill:
            matches = [entry for entry in skills if entry.name == path.name]
            if len(matches) == 1:
                skills = matches

        if list_:
            data = _list_data(
                skills,
                agents,
                scope=scope,
                project_root=project_root,
            )
            from usecli.cli.core.runtime import is_json_mode

            if not is_json_mode():
                _print_list(data)
            return data

        if path is not None:
            if len(skills) != 1:
                raise UsecliBadParameter(
                    "--path requires exactly one skill; use --skill to choose one"
                )
            scope = "custom"
            target = path.expanduser().resolve() / "SKILL.md"
            try:
                status = install_skill(skills[0], target, force=force)
            except OSError as error:
                status = f"error: {error}"
            results = [
                InstallResult(
                    skill=skills[0].name,
                    agent="custom",
                    path=target,
                    status=status,
                )
            ]
        else:
            results = install_skills(
                skills,
                agents=agents,
                scope=scope,
                project_root=project_root,
                force=force,
            )

        errors = [
            f"{result.skill} -> {result.agent}: {result.status}"
            for result in results
            if result.status.startswith("error:")
        ]
        data: dict[str, Any] = {
            "scope": scope,
            "skills": [skill.name for skill in skills],
            "installed": [
                {
                    "skill": result.skill,
                    "agent": result.agent,
                    "path": str(result.path),
                    "status": result.status,
                }
                for result in results
            ],
            "errors": errors,
        }

        from usecli.cli.core.runtime import is_json_mode

        if not is_json_mode():
            _print_results(data)
        return data
