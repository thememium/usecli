"""MakeThemeCommand - CLI command."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
from rich.console import Console

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.scaffold import ScaffoldError, make_theme
from usecli.shared.config.manager import find_project_root, get_config, reset_config

console = Console()


class MakeThemeCommand(BaseCommand):
    def visible(self) -> bool:
        command_name = os.path.basename(sys.argv[0]) if sys.argv else ""
        return command_name == "usecli"

    def signature(self) -> str:
        return "make:theme"

    def description(self) -> str:
        return "Create a new theme file"

    def handle(self, name: str = typer.Argument(..., help="Theme config name")) -> None:
        config = get_config()
        current_root = find_project_root(Path.cwd()) or Path.cwd().resolve()
        if config.get_project_root().resolve() != current_root:
            reset_config()
            config = get_config()

        try:
            target_file = make_theme(name, config=config)
        except ScaffoldError as error:
            console.print(f"[{COLOR.ERROR}]Error: {error}[/{COLOR.ERROR}]")
            return

        console.print(
            f"[{COLOR.SUCCESS}]Successfully created theme at "
            f"{target_file}[/{COLOR.SUCCESS}]"
        )
