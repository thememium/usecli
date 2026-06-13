"""Make command for generating new CLI commands."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

from usecli.cli.core.base_command import BaseCommand
from usecli.shared.config.globals import TEMPLATES_DIR
from usecli.shared.config.manager import find_project_root, get_config, reset_config


def _lazy_console():
    from rich.console import Console
    return Console()


_LAZY_IMPORTS = {
    "Template": "jinja2",
    "pascalcase": "caseconverter",
    "snakecase": "caseconverter",
    "COLOR": "usecli.cli.config.colors",
}

_console = None

def __getattr__(name: str):
    global _console
    if name == "console":
        if _console is None:
            _console = _lazy_console()
        return _console
    module_name = _LAZY_IMPORTS.get(name)
    if module_name is not None:
        from importlib import import_module
        value = getattr(import_module(module_name), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class MakeCommand(BaseCommand):
    """Command for generating new CLI command files."""

    def visible(self) -> bool:
        command_name = os.path.basename(sys.argv[0]) if sys.argv else ""
        return command_name == "usecli"

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

        config = get_config()
        current_root = find_project_root(Path.cwd()) or Path.cwd().resolve()
        if config.get_project_root().resolve() != current_root:
            reset_config()
            config = get_config()
        project_paths = config.get_project_paths()
        commands_dir = project_paths["commands_dir"]
        commands_dir.mkdir(parents=True, exist_ok=True)
        target_file = commands_dir / file_name

        if target_file.exists():
            console.print(
                f"[{COLOR.ERROR}]Error: Command file {target_file} already exists.[/{COLOR.ERROR}]"
            )
            return
        templates_dir = project_paths["templates_dir"]
        project_template_path = templates_dir / "command.py.j2"
        if project_template_path.exists():
            template_path = project_template_path
        else:
            template_path = TEMPLATES_DIR / "command.py.j2"
        template = Template(template_path.read_text())
        rendered_content = template.render(
            class_name=class_name, command_name=command_name
        )

        target_file.write_text(rendered_content)
        console.print(
            f"[{COLOR.SUCCESS}]Successfully created {name} command at {target_file}[/{COLOR.SUCCESS}]"
        )
