"""Install a usecli skill for AI coding agents."""

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
from usecli.shared.config.manager import find_project_root

console = Console()

SKILL_NAME = "usecli"
SKILL_FILENAME = "SKILL.md"

# AgentSkills standard locations. Claude Code only reads its own directory;
# Codex and Cursor both read `.agents/skills`, and Cursor also reads
# `.cursor/skills`. Copying the same SKILL.md to all three is intentional:
# agents cannot consume files they do not scan.
AGENT_TARGETS: dict[str, str] = {
    "claude-code": ".claude/skills/{name}",
    "codex": ".agents/skills/{name}",
    "cursor": ".cursor/skills/{name}",
}
AGENT_ALIASES = {"claude": "claude-code", "agents": "codex"}
DEFAULT_AGENTS = tuple(AGENT_TARGETS)


def _parse_agents(agents: list[str] | None) -> list[str]:
    """Expand ``--agent`` values, including ``all`` and comma-separated names."""
    if not agents:
        return list(DEFAULT_AGENTS)

    selected: list[str] = []
    for raw in agents:
        for part in raw.split(","):
            name = part.strip().lower()
            if not name:
                continue
            if name == "all":
                selected.extend(DEFAULT_AGENTS)
                continue
            name = AGENT_ALIASES.get(name, name)
            if name not in AGENT_TARGETS:
                choices = ", ".join(["all", *AGENT_TARGETS])
                raise UsecliBadParameter(
                    f"Unknown agent {name!r}. Choose one of: {choices}"
                )
            selected.append(name)

    if not selected:
        raise UsecliBadParameter("At least one agent is required")

    return list(dict.fromkeys(selected))


def _project_root() -> Path:
    return find_project_root(Path.cwd()) or Path.cwd().resolve()


def _target_dir(agent: str, *, global_: bool, project_root: Path) -> Path:
    template = AGENT_TARGETS[agent]
    base = Path.home() if global_ else project_root
    return base / template.format(name=SKILL_NAME)


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
    """Render the skill document for the current app and project."""
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


def write_skill(target_file: Path, content: str, *, force: bool) -> str:
    """Write one skill file, returning ``created``/``updated``/``skipped``/``unchanged``."""
    if target_file.exists():
        if target_file.read_text(encoding="utf-8") == content:
            return "unchanged"
        if not force:
            return "skipped"
        target_file.write_text(content, encoding="utf-8")
        return "updated"

    target_file.parent.mkdir(parents=True, exist_ok=True)
    target_file.write_text(content, encoding="utf-8")
    return "created"


class InstallSkillCommand(BaseCommand):
    """Install a usecli skill for AI coding agents."""

    def signature(self) -> str:
        return "skill:install"

    def description(self) -> str:
        return "Install a usecli skill for coding agents"

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
                    "Agent target: all, claude-code, codex, or cursor. "
                    "Repeat or comma-separate for multiple agents."
                ),
            ),
        ] = None,
        path: Annotated[
            Path | None,
            typer.Option(
                "--path",
                help="Install into this exact skill directory instead of an agent directory.",
            ),
        ] = None,
        force: Annotated[
            bool,
            typer.Option(
                "--force",
                "-f",
                help="Overwrite an existing SKILL.md with different content.",
            ),
        ] = False,
    ) -> dict[str, Any]:
        if global_ and path is not None:
            raise UsecliBadParameter("--global and --path cannot be used together")
        if path is not None and agent:
            raise UsecliBadParameter("--path and --agent cannot be used together")

        project_root = _project_root()
        command_name = get_script_command_name(default="usecli") or "usecli"

        if path is not None:
            scope = "custom"
            targets = [("custom", path.expanduser().resolve())]
        else:
            scope = "global" if global_ else "project"
            targets = [
                (name, _target_dir(name, global_=global_, project_root=project_root))
                for name in _parse_agents(agent)
            ]

        content = render_skill(self.app, command_name=command_name)
        installed: list[dict[str, str]] = []
        for name, directory in targets:
            target_file = directory / SKILL_FILENAME
            status = write_skill(target_file, content, force=force)
            installed.append(
                {"agent": name, "path": str(target_file), "status": status}
            )

        data: dict[str, Any] = {
            "skill": SKILL_NAME,
            "command_name": command_name,
            "scope": scope,
            "installed": installed,
        }

        from usecli.cli.core.runtime import is_json_mode

        if is_json_mode():
            return data

        console.print()
        for result in installed:
            color = {
                "created": COLOR.SUCCESS,
                "updated": COLOR.SUCCESS,
                "unchanged": COLOR.FOREGROUND_MUTED,
                "skipped": COLOR.WARNING,
            }[result["status"]]
            console.print(
                f"[{color}]{result['status'].capitalize()}[/{color}] {result['path']}"
            )
        console.print()
        console.print(
            f"[bold {COLOR.PRIMARY}]usecli skill installed for {scope} scope[/bold {COLOR.PRIMARY}]"
        )
        if any(result["status"] == "skipped" for result in installed):
            console.print(
                f"[{COLOR.WARNING}]Existing skill files were left untouched. "
                f"Re-run with --force to overwrite them.[/{COLOR.WARNING}]"
            )
        console.print()

        return data
