"""InitCommand - Initialize usecli in the current project."""

from __future__ import annotations

import re
from pathlib import Path

import typer
from jinja2 import Template
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from usecli.cli.core.base_command import BaseCommand

console = Console()


class InitCommand(BaseCommand):
    def signature(self) -> str:
        return "init"

    def description(self) -> str:
        return "Initialize usecli in the current project"

    def _replace_config_in_pyproject(
        self, pyproject_path: Path, config_content: str
    ) -> None:
        """Replace existing [tool.usecli] section in pyproject.toml."""
        content = pyproject_path.read_text()

        # Pattern to match [tool.usecli] section until next section or end of file
        pattern = r"\[tool\.usecli\].*?(?=\n\[|\Z)"
        replacement = config_content.strip()

        # Replace the existing section
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        pyproject_path.write_text(new_content)

    def _has_existing_config(
        self, pyproject_path: Path, config_toml_path: Path
    ) -> bool:
        """Check if usecli config already exists."""
        if pyproject_path.exists() and "[tool.usecli]" in pyproject_path.read_text():
            return True
        if config_toml_path.exists():
            return True
        return False

    def _get_config_source(
        self, pyproject_path: Path, config_toml_path: Path
    ) -> str | None:
        """Get the source of existing config."""
        if pyproject_path.exists() and "[tool.usecli]" in pyproject_path.read_text():
            return "pyproject.toml"
        if config_toml_path.exists():
            return "usecli.config.toml"
        return None

    def handle(
        self,
        title: str = typer.Option("My CLI", help="Title for your CLI"),
        description: str = typer.Option(
            "A custom CLI tool", help="Description for your CLI"
        ),
        commands_dir: str = typer.Option(
            "commands", help="Directory for custom commands"
        ),
        force: bool = typer.Option(
            False, "--force", "-f", help="Overwrite existing config without prompting"
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

        # Check if config already exists
        existing_source = self._get_config_source(pyproject_path, config_toml_path)

        if existing_source and not force:
            should_overwrite = Confirm.ask(
                f"[yellow]usecli config already exists in {existing_source}.[/yellow]\n"
                f"Do you want to overwrite it?",
                default=False,
            )
            if not should_overwrite:
                console.print("[yellow]Skipping config update.[/yellow]")
                return

        # Check if pyproject.toml exists
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            if "[tool.usecli]" in content:
                self._replace_config_in_pyproject(pyproject_path, config_content)
                console.print(
                    f"[green]Updated [tool.usecli] in {pyproject_path}[/green]"
                )
            else:
                with open(pyproject_path, "a") as f:
                    f.write("\n\n" + config_content)
                console.print(f"[green]Added [tool.usecli] to {pyproject_path}[/green]")
        else:
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
