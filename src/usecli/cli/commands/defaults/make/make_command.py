"""Make command for generating new CLI commands."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
from rich.console import Console

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.scaffold import ScaffoldError, make_command
from usecli.shared.config.manager import find_project_root, get_config, reset_config

console = Console()


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
        config = get_config()
        current_root = find_project_root(Path.cwd()) or Path.cwd().resolve()
        if config.get_project_root().resolve() != current_root:
            reset_config()
            config = get_config()

        try:
            target_file = make_command(name, config=config)
        except ScaffoldError as error:
            console.print(f"[{COLOR.ERROR}]Error: {error}[/{COLOR.ERROR}]")
            return

        console.print(
            f"[{COLOR.SUCCESS}]Successfully created {name} command at "
            f"{target_file}[/{COLOR.SUCCESS}]"
        )
