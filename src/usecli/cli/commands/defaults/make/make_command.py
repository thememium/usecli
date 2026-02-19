"""Make command for generating new CLI commands."""

from __future__ import annotations

import typer
from caseconverter import pascalcase, snakecase
from jinja2 import Template
from rich.console import Console

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.shared.config.globals import TEMPLATES_DIR
from usecli.shared.config.manager import get_config

console = Console()


class MakeCommand(BaseCommand):
    """Command for generating new CLI command files."""

    def visible(self) -> bool:
        config = get_config()
        return not config.get("hide_make_command", False)

    def signature(self) -> str:
        """Return the command signature."""
        return "make:command"

    def description(self) -> str:
        """Return the command description."""
        return "Create a new CLI command"

    def handle(
        self, name: str = typer.Argument(..., help="The name of the command")
    ) -> None:
        """Handle the command execution.

        Args:
            name: The name of the command to create.
        """
        clean_name = name.replace("Command", "").replace("command", "")
        class_name = pascalcase(clean_name.replace(":", "_")) + "Command"
        command_name = snakecase(clean_name.replace(":", "_"))
        file_name = f"{snakecase(clean_name.replace(':', '_'))}_command.py"

        commands_dir = get_config().get_project_commands_dir()
        commands_dir.mkdir(parents=True, exist_ok=True)
        target_file = commands_dir / file_name

        if target_file.exists():
            console.print(
                f"[{COLOR.ERROR}]Error: Command file {target_file} already exists.[/{COLOR.ERROR}]"
            )
            return
        template = Template((TEMPLATES_DIR / "command.py.j2").read_text())
        rendered_content = template.render(
            class_name=class_name, command_name=command_name
        )

        target_file.write_text(rendered_content)
        console.print(
            f"[{COLOR.SUCCESS}]Successfully created {name} command at {target_file}[/{COLOR.SUCCESS}]"
        )
