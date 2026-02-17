"""InitCommand - Initialize usecli in the current project."""

from __future__ import annotations

from pathlib import Path

import typer
from jinja2 import Template
from rich.console import Console
from rich.panel import Panel

from usecli.cli.core.base_command import BaseCommand

console = Console()


class InitCommand(BaseCommand):
    def signature(self) -> str:
        return "init"

    def description(self) -> str:
        return "Initialize usecli in the current project"

    def handle(
        self,
        title: str = typer.Option("My CLI", help="Title for your CLI"),
        description: str = typer.Option(
            "A custom CLI tool", help="Description for your CLI"
        ),
        commands_dir: str = typer.Option(
            "commands", help="Directory for custom commands"
        ),
    ) -> None:
        cwd = Path.cwd()
        pyproject_path = cwd / "pyproject.toml"
        config_toml_path = cwd / "usecli.config.toml"
        commands_path = cwd / commands_dir

        # Create the commands directory
        if not commands_path.exists():
            commands_path.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]Created commands directory:[/green] {commands_path}")
        else:
            console.print(
                f"[yellow]Commands directory already exists:[/yellow] {commands_path}"
            )

        # Load the template
        template_path = Path(__file__).parent.parent / "templates" / "usecli.toml.j2"
        template_content = template_path.read_text()
        template = Template(template_content)

        # Render the config
        config_content = template.render(
            title=title,
            description=description,
            commands_dir=commands_dir,
        )

        # Check if pyproject.toml exists
        if pyproject_path.exists():
            # Check if [tool.usecli] already exists
            content = pyproject_path.read_text()
            if "[tool.usecli]" in content:
                console.print(
                    f"[yellow][tool.usecli] already exists in {pyproject_path}[/yellow]"
                )
            else:
                # Append to pyproject.toml
                with open(pyproject_path, "a") as f:
                    f.write("\n\n" + config_content)
                console.print(f"[green]Added [tool.usecli] to {pyproject_path}[/green]")
        else:
            # Create usecli.config.toml
            config_toml_path.write_text(config_content)
            console.print(f"[green]Created {config_toml_path}[/green]")

        # Show summary
        console.print(
            Panel.fit(
                f"[bold green]usecli initialized![/bold green]\n\n"
                f"Title: {title}\n"
                f"Description: {description}\n"
                f"Commands Directory: {commands_dir}\n\n"
                f"Create new commands with: [bold]usecli make:command <name>[/bold]",
                title="usecli Init",
                border_style="green",
            )
        )
