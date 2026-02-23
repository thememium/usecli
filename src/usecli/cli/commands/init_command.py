"""InitCommand - Initialize usecli in the current project."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer
from jinja2 import Template
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import pyfiglet

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.cli.core.exceptions import UsecliBadParameter
from usecli.cli.core.validators import validate_command_name
from usecli.cli.utils.interactive.terminal_menu import terminal_menu
from usecli.shared.config.globals import TEMPLATES_DIR, THEMES_DIR, USECLI_TOML
from usecli.shared.config.manager import ConfigManager, get_config

console = Console()


class InitCommand(BaseCommand):
    def visible(self) -> bool:
        config = get_config()
        return not config.get("hide_init", False)

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
        replacement = config_content.rstrip() + "\n"

        # Replace the existing section
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

        pyproject_path.write_text(new_content)

    def _get_config_source(self, pyproject_path: Path) -> str | None:
        """Get the source of existing config."""
        if pyproject_path.exists() and "[tool.usecli]" in pyproject_path.read_text():
            return "pyproject.toml"
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

    def _write_usecli_toml(
        self, project_root: Path, config_content: str, force: bool
    ) -> str:
        config_path = project_root / USECLI_TOML
        existed = config_path.exists()
        if existed and not force:
            should_overwrite = Confirm.ask(
                f"[{COLOR.WARNING}]usecli.toml already exists at {config_path}.[/{COLOR.WARNING}]\n"
                "Overwrite it with the new settings from this init run?",
                default=False,
            )
            if not should_overwrite:
                return "skipped"

        config_path.write_text(config_content.rstrip() + "\n")
        return "updated" if existed else "created"

    def _ensure_project_scripts(
        self, pyproject_path: Path, command_name: str, force: bool
    ) -> str:
        if not pyproject_path.exists():
            return "missing"

        content = pyproject_path.read_text()
        entry_line = f'{command_name} = "usecli:main"'
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
            if target == "usecli:main":
                return "unchanged"

            if not force:
                should_overwrite = Confirm.ask(
                    f"[{COLOR.WARNING}]Existing [project.scripts] entry for '{command_name}' points to '{target}'.[/{COLOR.WARNING}]\n"
                    "Overwrite it with 'usecli:main'?",
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

    def _derive_templates_dir(self, commands_dir: str) -> str:
        commands_path = Path(commands_dir)
        parent = commands_path.parent
        if commands_path.is_absolute():
            return str(parent / "templates")
        if parent == Path("."):
            return "templates"
        return str(parent / "templates")

    def _derive_themes_dir(self, commands_dir: str) -> str:
        commands_path = Path(commands_dir)
        parent = commands_path.parent
        if commands_path.is_absolute():
            return str(parent / "themes")
        if parent == Path("."):
            return "themes"
        return str(parent / "themes")

    def _get_existing_usecli_script_name(self, pyproject_path: Path) -> str | None:
        if not pyproject_path.exists():
            return None

        try:
            data = tomllib.loads(pyproject_path.read_text())
        except (tomllib.TOMLDecodeError, OSError):
            return None

        scripts = data.get("project", {}).get("scripts", {})
        if not isinstance(scripts, dict):
            return None

        for name, target in scripts.items():
            if target == "usecli:main":
                return name

        return None

    def _sync_environment(self, cwd: Path, command_name: str) -> None:
        uv_path = shutil.which("uv")
        if uv_path:
            venv_path = cwd / ".venv"
            if not venv_path.exists():
                return
            result = subprocess.run(
                [uv_path, "sync"],
                capture_output=True,
                text=True,
                cwd=cwd,
            )
            if result.returncode == 0:
                console.print(
                    f"[{COLOR.SUCCESS}]Synced environment with '{command_name}' entry point[/{COLOR.SUCCESS}]"
                )
            else:
                console.print(
                    f"[{COLOR.WARNING}]Failed to sync environment. Run 'uv sync'[/{COLOR.WARNING}]"
                )
            return

        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", "."],
            capture_output=True,
            text=True,
            cwd=cwd,
        )
        if result.returncode == 0:
            console.print(
                f"[{COLOR.SUCCESS}]Installed CLI with pip for '{command_name}' entry point[/{COLOR.SUCCESS}]"
            )
        else:
            console.print(
                f"[{COLOR.WARNING}]Failed to install with pip. Run 'pip install -e .'[/{COLOR.WARNING}]"
            )

    def _get_project_name_from_pyproject(self, pyproject_path: Path) -> str | None:
        if not pyproject_path.exists():
            return None

        try:
            data = tomllib.loads(pyproject_path.read_text())
        except (tomllib.TOMLDecodeError, OSError):
            return None

        return data.get("project", {}).get("name")

    def _prompt_command_name(self, command_name: str) -> str:
        prompt_text = (
            f"[bold {COLOR.SECONDARY}]CLI command name[/bold {COLOR.SECONDARY}]"
            " (entry point users run, e.g. mycli)"
        )
        first_attempt = True
        while True:
            if not first_attempt:
                console.print()
            first_attempt = False
            value = Prompt.ask(prompt_text, default=command_name)
            try:
                return validate_command_name(value)
            except UsecliBadParameter as error:
                error.show()

    def _get_figlet_fonts(self) -> list[str]:
        """Get a list of available figlet fonts."""

        fonts = pyfiglet.FigletFont.getFonts()
        return sorted(fonts)

    def _hex_to_rgb(self, value: str) -> tuple[int, int, int] | None:
        if not isinstance(value, str):
            return None
        value = value.strip()
        if not value:
            return None
        if value.startswith("#"):
            value = value[1:]
        if len(value) == 3:
            value = "".join(ch * 2 for ch in value)
        if len(value) != 6:
            return None
        try:
            r = int(value[0:2], 16)
            g = int(value[2:4], 16)
            b = int(value[4:6], 16)
        except ValueError:
            return None
        return r, g, b

    def _ansi_from_hex(self, value: str, *, background: bool = False) -> str | None:
        rgb = self._hex_to_rgb(value)
        if rgb is None:
            return None
        r, g, b = rgb
        prefix = "48" if background else "38"
        return f"\033[{prefix};2;{r};{g};{b}m"

    def _load_theme_colors(self, theme_path: Path) -> dict[str, str]:
        try:
            data = tomllib.loads(theme_path.read_text())
        except (tomllib.TOMLDecodeError, OSError):
            return {}
        colors = data.get("colors", {})
        if not isinstance(colors, dict):
            return {}
        return {key: value for key, value in colors.items() if isinstance(value, str)}

    def _format_theme_color_line(
        self, label: str, value: str, *, background: bool = False
    ) -> str:
        ansi = self._ansi_from_hex(value, background=background) if value else None
        reset = "\033[0m" if ansi else ""
        if ansi:
            if background:
                swatch = f"{ansi}##{reset}"
            else:
                swatch = f"{ansi}##{reset}"
        else:
            swatch = "##"
        display_value = value if value else "--"
        return f"{label:<16} {swatch} {display_value}"

    def _render_theme_preview(self, theme_path: Path | None) -> str:
        if theme_path is None:
            return "Theme preview unavailable."
        colors = self._load_theme_colors(theme_path)
        lines = [f"Theme: {theme_path.stem}", ""]
        palette = [
            ("primary", "Primary", False),
            ("secondary", "Secondary", False),
            ("accent", "Accent", False),
            ("success", "Success", False),
            ("warning", "Warning", False),
            ("error", "Error", False),
            ("info", "Info", False),
            ("foreground", "Foreground", False),
            ("foreground_muted", "Muted", False),
            ("background", "Background", True),
            ("border", "Border", False),
            ("panel_primary", "Panel Primary", False),
            ("panel_secondary", "Panel Secondary", False),
            ("panel_accent", "Panel Accent", False),
            ("command", "Command", False),
            ("option", "Option", False),
            ("link", "Link", False),
            ("prompt", "Prompt", False),
        ]
        for key, label, background in palette:
            lines.append(
                self._format_theme_color_line(
                    label, colors.get(key, ""), background=background
                )
            )
        return "\n".join(lines)

    def _get_theme_files(self, themes_path: Path) -> list[Path]:
        theme_dirs = [themes_path, THEMES_DIR]
        theme_map: dict[str, Path] = {}
        for theme_dir in theme_dirs:
            if not theme_dir.exists():
                continue
            for path in theme_dir.glob("*.toml"):
                if not path.is_file():
                    continue
                name = path.stem
                if name not in theme_map:
                    theme_map[name] = path
        return [
            theme_map[name]
            for name in sorted(
                theme_map.keys(),
                key=lambda name: (name.lower() != "default", name.lower()),
            )
        ]

    def _prompt_theme(self, themes_path: Path, default_theme: str = "default") -> str:
        theme_files = self._get_theme_files(themes_path)
        if not theme_files:
            return default_theme
        theme_names = [path.stem for path in theme_files]
        theme_map = {path.stem: path for path in theme_files}
        console.print(
            f"[bold {COLOR.SECONDARY}]Select a theme for your CLI[/bold {COLOR.SECONDARY}]"
        )
        selection = terminal_menu(
            theme_names,
            search=True,
            search_key="/",
            show_search_hint=False,
            status_bar="Enter = select | / = search | J/K = move | D/U = page | Esc = quit",
            preview_command=lambda value: self._render_theme_preview(
                theme_map.get(value)
            ),
            preview_size=0.70,
        )
        selected_theme = selection[0] if selection else default_theme
        console.print()
        console.print(
            f"[bold {COLOR.PRIMARY}]Selected theme:[/bold {COLOR.PRIMARY}] {selected_theme}"
        )
        return selected_theme

    def _prompt_title_font(self, title: str, default_font: str = "big") -> str:
        fonts = self._get_figlet_fonts()
        console.print(
            f"[bold {COLOR.SECONDARY}]Select a figlet font for your CLI title[/bold {COLOR.SECONDARY}]"
        )
        selection = terminal_menu(
            fonts,
            search=True,
            search_key="/",
            show_search_hint=False,
            status_bar="Enter = select | / = search | J/K = move | D/U = page | Esc = quit",
            preview_command=lambda value: (
                f"{pyfiglet.figlet_format(title, font=value)}"
            ),
            preview_size=0.70,
        )
        selected_font = selection[0] if selection else default_font
        console.print()
        console.print(
            f"[bold {COLOR.PRIMARY}]Selected title font:[/bold {COLOR.PRIMARY}] {selected_font}"
        )
        return selected_font

    def _create_full_pyproject_toml(
        self,
        pyproject_path: Path,
        command_name: str,
        title: str,
        description: str,
        commands_dir: str,
        config_content: str,
    ) -> None:
        parts = Path(commands_dir).parts
        root_package = parts[0] if parts else "src"
        project_name = pyproject_path.parent.name

        pyproject_content = f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "{description}"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "usecli",
]
license = "MIT"

[project.scripts]
{command_name} = "usecli:main"

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["{root_package}*"]

{config_content}'''

        pyproject_path.write_text(pyproject_content)

    def handle(
        self,
        title: str = typer.Option("Use CLI", help="Title for your CLI"),
        description: str = typer.Option(
            "A custom CLI tool", help="Description for your CLI"
        ),
        commands_dir: str = typer.Option(
            "cli/commands", help="Directory for custom commands"
        ),
        command_name: Annotated[
            str,
            typer.Option(
                "--command-name",
                "-c",
                help="Command name for your CLI entry point",
                callback=validate_command_name,
            ),
        ] = "usecli",
        force: bool = typer.Option(
            False, "--force", "-f", help="Overwrite existing config without prompting"
        ),
    ) -> None:
        cwd = Path.cwd()
        config_manager = ConfigManager(start_dir=cwd)
        project_root = config_manager.get_project_root()
        pyproject_path = project_root / "pyproject.toml"

        console.print()
        existing_command_name = self._get_existing_usecli_script_name(pyproject_path)
        if existing_command_name and command_name == "usecli":
            command_name = existing_command_name

        project_name = self._get_project_name_from_pyproject(pyproject_path)
        if project_name and command_name == "usecli":
            command_name = project_name
        if project_name and title == "Use CLI":
            title = project_name

        console.print()
        console.rule(
            title=f"[bold {COLOR.PRIMARY}]── CLI identity[/bold {COLOR.PRIMARY}]",
            align="left",
            style=COLOR.PRIMARY,
        )
        console.print()
        command_name = self._prompt_command_name(command_name)
        console.print()
        title = Prompt.ask(
            f"[bold {COLOR.SECONDARY}]CLI title[/bold {COLOR.SECONDARY}]"
            " (displayed in help and banner)",
            default=title if title != "Use CLI" else command_name,
        )
        console.print()
        description = Prompt.ask(
            f"[bold {COLOR.SECONDARY}]CLI description[/bold {COLOR.SECONDARY}]"
            " (short summary shown in help)",
            default=description,
        )
        console.print()
        console.rule(
            title=f"[bold {COLOR.PRIMARY}]── Project structure[/bold {COLOR.PRIMARY}]",
            align="left",
            style=COLOR.PRIMARY,
        )
        console.print()
        commands_dir = Prompt.ask(
            f"[bold {COLOR.SECONDARY}]Commands directory[/bold {COLOR.SECONDARY}]"
            " (where command modules live)",
            default=commands_dir,
        )
        console.print()
        templates_dir = Prompt.ask(
            f"[bold {COLOR.SECONDARY}]Templates directory[/bold {COLOR.SECONDARY}]"
            " (scaffolding templates for make:command)",
            default=self._derive_templates_dir(commands_dir),
        )
        console.print()
        themes_dir = Prompt.ask(
            f"[bold {COLOR.SECONDARY}]Themes directory[/bold {COLOR.SECONDARY}]"
            " (theme TOML files for styling)",
            default=self._derive_themes_dir(commands_dir),
        )
        console.print()
        commands_path = (
            Path(commands_dir)
            if Path(commands_dir).is_absolute()
            else project_root / commands_dir
        )
        templates_path = (
            Path(templates_dir)
            if Path(templates_dir).is_absolute()
            else project_root / templates_dir
        )
        themes_path = (
            Path(themes_dir)
            if Path(themes_dir).is_absolute()
            else project_root / themes_dir
        )

        console.rule(
            title=f"[bold {COLOR.PRIMARY}]── Branding[/bold {COLOR.PRIMARY}]",
            align="left",
            style=COLOR.PRIMARY,
        )
        console.print()
        console.print()
        theme = self._prompt_theme(themes_path)
        console.print()
        title_font = self._prompt_title_font(title)
        raw_title = pyfiglet.figlet_format(text=title, font=title_font)
        title_text = "\n".join(" " + line for line in raw_title.split("\n"))
        console.print()
        console.print(f"[{COLOR.PRIMARY}]{title_text}")

        # Check if config already exists
        existing_source = self._get_config_source(pyproject_path)

        if existing_source and not force:
            should_overwrite = Confirm.ask(
                f"[{COLOR.WARNING}]usecli config already exists in {existing_source}.[/{COLOR.WARNING}]\n"
                "Overwrite it with the new settings from this init run?",
                default=False,
            )
            if not should_overwrite:
                console.print(
                    f"[{COLOR.WARNING}]Skipping config update.[/{COLOR.WARNING}]"
                )
                return

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

        if not templates_path.exists():
            templates_path.mkdir(parents=True, exist_ok=True)
            console.print(
                f"[{COLOR.SUCCESS}]Created templates directory:[/{COLOR.SUCCESS}] {templates_path}"
            )
        else:
            console.print(
                f"[{COLOR.WARNING}]Templates directory already exists:[/{COLOR.WARNING}] {templates_path}"
            )

        if not themes_path.exists():
            themes_path.mkdir(parents=True, exist_ok=True)
            console.print(
                f"[{COLOR.SUCCESS}]Created themes directory:[/{COLOR.SUCCESS}] {themes_path}"
            )
        else:
            console.print(
                f"[{COLOR.WARNING}]Themes directory already exists:[/{COLOR.WARNING}] {themes_path}"
            )

        if self._ensure_package_init_files(commands_path, cwd):
            console.print(
                f"[{COLOR.SUCCESS}]Added __init__.py files for package discovery[/{COLOR.SUCCESS}]"
            )

        make_template_path = templates_path / "command.py.j2"
        if not make_template_path.exists():
            shutil.copy(TEMPLATES_DIR / "command.py.j2", make_template_path)
            console.print(
                f"[{COLOR.SUCCESS}]Added make command template:[/{COLOR.SUCCESS}] {make_template_path}"
            )
        else:
            console.print(
                f"[{COLOR.WARNING}]Make command template already exists:[/{COLOR.WARNING}] {make_template_path}"
            )

        theme_template_path = themes_path / "default.toml"
        if not theme_template_path.exists() and (THEMES_DIR / "default.toml").exists():
            shutil.copy(THEMES_DIR / "default.toml", theme_template_path)
            console.print(
                f"[{COLOR.SUCCESS}]Added default theme:[/{COLOR.SUCCESS}] {theme_template_path}"
            )
        elif theme_template_path.exists():
            console.print(
                f"[{COLOR.WARNING}]Default theme already exists:[/{COLOR.WARNING}] {theme_template_path}"
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
            templates_dir=templates_dir,
            themes_dir=themes_dir,
            title_font=title_font,
            theme=theme,
        )

        scripts_status: str | None = None
        usecli_toml_status: str | None = None

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

            scripts_status = self._ensure_project_scripts(
                pyproject_path, command_name, force
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
                self._sync_environment(project_root, command_name)
        else:
            self._create_full_pyproject_toml(
                pyproject_path,
                command_name,
                title,
                description,
                commands_dir,
                config_content,
            )
            console.print(
                f"[{COLOR.SUCCESS}]Created {pyproject_path}[/{COLOR.SUCCESS}]"
            )
            scripts_status = "added"

            self._sync_environment(project_root, command_name)

        usecli_toml_status = self._write_usecli_toml(
            project_root, config_content, force
        )
        if usecli_toml_status == "created":
            console.print(
                f"[{COLOR.SUCCESS}]Created {USECLI_TOML} for runtime config fallback[/{COLOR.SUCCESS}]"
            )
        elif usecli_toml_status == "updated":
            console.print(
                f"[{COLOR.SUCCESS}]Updated {USECLI_TOML} for runtime config fallback[/{COLOR.SUCCESS}]"
            )
        elif usecli_toml_status == "skipped":
            console.print(
                f"[{COLOR.WARNING}]Skipped updating {USECLI_TOML}.[/{COLOR.WARNING}]"
            )

        # Show summary
        summary_command = (
            command_name
            if scripts_status in {"added", "updated", "unchanged"}
            else None
        )
        command_summary = ""
        if summary_command:
            command_summary = (
                f"Command: {summary_command}\n\n"
                f"Create new commands with: [bold {COLOR.COMMAND}]{summary_command} make:command <name>[/bold {COLOR.COMMAND}]"
            )
        else:
            command_summary = "Create new commands after adding a [project.scripts] entry for usecli:main."
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
