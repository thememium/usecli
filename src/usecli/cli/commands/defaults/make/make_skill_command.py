"""Create a new bundled Agent Skill for this CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from jinja2 import Template
from rich.console import Console

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.cli.core.validators import validate_skill_name
from usecli.shared.config.globals import TEMPLATES_DIR
from usecli.shared.config.manager import find_project_root, get_config, reset_config

console = Console()


def _frontmatter_description(value: str) -> str:
    normalized = " ".join(value.split())
    return normalized.replace("\\", "\\\\").replace('"', '\\"')


class MakeSkillCommand(BaseCommand):
    """Scaffold a skill that ships with this CLI."""

    def signature(self) -> str:
        return "make:skill"

    def description(self) -> str:
        return "Create a new bundled skill"

    def handle(
        self,
        name: str = typer.Argument(..., help="Skill name (lowercase-with-hyphens)"),
        description: Annotated[
            str,
            typer.Option(
                "--description",
                "-d",
                help="Short description used in the skill frontmatter",
            ),
        ] = "",
    ) -> None:
        validate_skill_name(name)

        config = get_config()
        current_root = find_project_root(Path.cwd()) or Path.cwd().resolve()
        if config.get_project_root().resolve() != current_root:
            reset_config()
            config = get_config()

        skills_dir = config.get_project_skills_dir()
        target_dir = skills_dir / name
        target_file = target_dir / "SKILL.md"
        if target_file.exists():
            console.print(
                f"[{COLOR.ERROR}]Error: Skill {target_file} already exists."
                f"[/{COLOR.ERROR}]"
            )
            return

        command_name = config.get("command_name") or "usecli"
        command_name = " ".join(str(command_name).split()) or "usecli"
        description = _frontmatter_description(
            description or f"Use the {name} skill with the {command_name} CLI."
        )

        template = Template(
            (TEMPLATES_DIR / "project_skill.md.j2").read_text(encoding="utf-8"),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        content = template.render(
            name=name,
            description=description,
            command_name=command_name,
        )

        target_dir.mkdir(parents=True, exist_ok=True)
        target_file.write_text(content, encoding="utf-8")
        console.print(
            f"[{COLOR.SUCCESS}]Successfully created skill at {target_file}"
            f"[/{COLOR.SUCCESS}]"
        )
        console.print(
            f"[{COLOR.FOREGROUND_MUTED}]Add it to an agent with: "
            f"{command_name} skill:install --skill {name}"
            f"[/{COLOR.FOREGROUND_MUTED}]"
        )
