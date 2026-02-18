"""InitCommand - Initialize usecli in the current project."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import typer
from jinja2 import Template
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.cli.core.ui.title import get_script_command_name

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

    def _ensure_build_system(self, pyproject_path: Path) -> bool:
        if not pyproject_path.exists():
            return False

        content = pyproject_path.read_text()
        if "[build-system]" in content:
            return False

        build_system = (
            "[build-system]\n"
            'requires = ["setuptools>=68", "wheel"]\n'
            'build-backend = "setuptools.build_meta"\n'
        )
        pyproject_path.write_text(content.rstrip() + f"\n\n{build_system}\n")
        return True

    def _add_setuptools_package_discovery(
        self, pyproject_path: Path, commands_dir: str
    ) -> bool:
        if not pyproject_path.exists():
            return False

        content = pyproject_path.read_text()
        if "[tool.setuptools.packages.find]" in content:
            return False

        parts = Path(commands_dir).parts
        if not parts:
            return False

        root_package = parts[0]
        discovery_block = (
            "[tool.setuptools.packages.find]\n"
            'where = ["."]\n'
            f'include = ["{root_package}*"]\n\n'
        )

        if "[tool.usecli]" in content:
            content = content.replace(
                "[tool.usecli]",
                f"{discovery_block}[tool.usecli]",
            )
        else:
            content = content.rstrip() + f"\n\n{discovery_block}"

        pyproject_path.write_text(content)
        return True

    def _ensure_project_scripts(
        self, pyproject_path: Path, command_name: str, force: bool
    ) -> str:
        if not pyproject_path.exists():
            return "missing"

        content = pyproject_path.read_text()
        entry_line = f'{command_name} = "usecli:run_app"'
        section_pattern = r"\[project\.scripts\].*?(?=\n\[|\Z)"
        match = re.search(section_pattern, content, flags=re.DOTALL)

        if not match:
            new_content = content.rstrip() + f"\n\n[project.scripts]\n{entry_line}\n"
            pyproject_path.write_text(new_content)
            return "added"

        block = match.group(0)
        entry_pattern = (
            rf"^\s*{re.escape(command_name)}\s*=\s*[\"\'](?P<target>[^\"\']+)[\"\']\s*$"
        )
        entry_match = re.search(entry_pattern, block, flags=re.MULTILINE)

        if entry_match:
            target = entry_match.group("target")
            if target == "usecli:run_app":
                return "unchanged"

            if not force:
                should_overwrite = Confirm.ask(
                    f"[{COLOR.WARNING}]Existing [project.scripts] entry for '{command_name}' detected.[/{COLOR.WARNING}]\n"
                    "Do you want to overwrite it?",
                    default=False,
                )
                if not should_overwrite:
                    return "skipped"

            updated_block = re.sub(
                entry_pattern,
                entry_line,
                block,
                flags=re.MULTILINE,
            )
            new_content = (
                content[: match.start()] + updated_block + content[match.end() :]
            )
            pyproject_path.write_text(new_content)
            return "updated"

        updated_block = block.rstrip() + f"\n{entry_line}\n"
        new_content = content[: match.start()] + updated_block + content[match.end() :]
        pyproject_path.write_text(new_content)
        return "added"

    def _ensure_package_init_files(self, commands_path: Path, cwd: Path) -> bool:
        created = False
        init_paths = [commands_path / "__init__.py"]
        if commands_path.parent != cwd:
            init_paths.append(commands_path.parent / "__init__.py")

        for init_path in init_paths:
            if not init_path.exists():
                init_path.touch()
                created = True

        return created

    def handle(
        self,
        title: str = typer.Option("My CLI", help="Title for your CLI"),
        description: str = typer.Option(
            "A custom CLI tool", help="Description for your CLI"
        ),
        commands_dir: str = typer.Option(
            "cli/commands", help="Directory for custom commands"
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
            console.print(
                f"[{COLOR.SUCCESS}]Created commands directory:[/{COLOR.SUCCESS}] {commands_path}"
            )
        else:
            console.print(
                f"[{COLOR.WARNING}]Commands directory already exists:[/{COLOR.WARNING}] {commands_path}"
            )

        if self._ensure_package_init_files(commands_path, cwd):
            console.print(
                f"[{COLOR.SUCCESS}]Added __init__.py files for package discovery[/{COLOR.SUCCESS}]"
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
                f"[{COLOR.WARNING}]usecli config already exists in {existing_source}.[/{COLOR.WARNING}]\n"
                f"Do you want to overwrite it?",
                default=False,
            )
            if not should_overwrite:
                console.print(
                    f"[{COLOR.WARNING}]Skipping config update.[/{COLOR.WARNING}]"
                )
                return

        # Check if pyproject.toml exists
        if pyproject_path.exists():
            content = pyproject_path.read_text()
            if "[tool.usecli]" in content:
                self._replace_config_in_pyproject(pyproject_path, config_content)
                console.print(
                    f"[{COLOR.SUCCESS}]Updated [tool.usecli] in {pyproject_path}[/{COLOR.SUCCESS}]"
                )
            else:
                with open(pyproject_path, "a") as f:
                    f.write("\n\n" + config_content)
                console.print(
                    f"[{COLOR.SUCCESS}]Added [tool.usecli] to {pyproject_path}[/{COLOR.SUCCESS}]"
                )

            script_command = get_script_command_name(default="usecli") or "usecli"
            scripts_status = self._ensure_project_scripts(
                pyproject_path, script_command, force
            )
            if scripts_status == "added":
                console.print(
                    f"[{COLOR.SUCCESS}]Added [project.scripts] to {pyproject_path}[/{COLOR.SUCCESS}]"
                )
            elif scripts_status == "updated":
                console.print(
                    f"[{COLOR.SUCCESS}]Updated [project.scripts] in {pyproject_path}[/{COLOR.SUCCESS}]"
                )
            elif scripts_status == "skipped":
                console.print(
                    f"[{COLOR.WARNING}]Skipped [project.scripts] update.[/{COLOR.WARNING}]"
                )

            if self._ensure_build_system(pyproject_path):
                console.print(
                    f"[{COLOR.SUCCESS}]Added build-system to pyproject.toml[/{COLOR.SUCCESS}]"
                )
            if self._add_setuptools_package_discovery(pyproject_path, commands_dir):
                console.print(
                    f"[{COLOR.SUCCESS}]Added setuptools package discovery to pyproject.toml[/{COLOR.SUCCESS}]"
                )

            if scripts_status in {"added", "updated", "unchanged"}:
                venv_path = cwd / ".venv"
                if venv_path.exists():
                    uv_path = shutil.which("uv")
                    if uv_path:
                        result = subprocess.run(
                            [uv_path, "sync"],
                            capture_output=True,
                            text=True,
                        )
                        if result.returncode == 0:
                            console.print(
                                f"[{COLOR.SUCCESS}]Synced environment with '{script_command}' entry point[/{COLOR.SUCCESS}]"
                            )
                        else:
                            console.print(
                                f"[{COLOR.WARNING}]Failed to sync environment. Run 'uv sync'[/{COLOR.WARNING}]"
                            )
                    else:
                        console.print(
                            f"[{COLOR.WARNING}]uv not found. Run 'uv sync' to enable '{script_command}'[/{COLOR.WARNING}]"
                        )
        else:
            config_toml_path.write_text(config_content)
            console.print(
                f"[{COLOR.SUCCESS}]Created {config_toml_path}[/{COLOR.SUCCESS}]"
            )
            console.print(
                f"[{COLOR.WARNING}]Note: To create a CLI entry point, add this to your pyproject.toml:[/{COLOR.WARNING}]\n"
                f"[project.scripts]\n"
                f'usecli = "usecli:run_app"'
            )

        # Show summary
        summary_command = get_script_command_name()
        command_summary = ""
        if summary_command:
            command_summary = (
                f"Command: {summary_command}\n\n"
                f"Create new commands with: [bold {COLOR.COMMAND}]{summary_command} make:command <name>[/bold {COLOR.COMMAND}]"
            )
        else:
            command_summary = "Create new commands after adding a [project.scripts] entry for usecli:run_app."
        console.print(
            Panel.fit(
                f"[bold {COLOR.PRIMARY}]usecli initialized![/bold {COLOR.PRIMARY}]\n\n"
                f"Title: {title}\n"
                f"Description: {description}\n"
                f"Commands Directory: {commands_dir}\n"
                f"{command_summary}",
                title="usecli Init",
                border_style=COLOR.PANEL_PRIMARY,
            )
        )
