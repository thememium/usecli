"""MakeThemeCommand - CLI command."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer
from jinja2 import Template
from rich.console import Console

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.shared.config.globals import TEMPLATES_DIR
from usecli.shared.config.manager import (ConfigManager, find_project_root,
                                          get_config, reset_config)

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
        clean_name = name.strip()
        if not clean_name:
            console.print(
                f"[{COLOR.ERROR}]Error: Theme name cannot be empty.[/{COLOR.ERROR}]"
            )
            return

        config = get_config()
        current_root = find_project_root(Path.cwd()) or Path.cwd().resolve()
        if config.get_project_root().resolve() != current_root:
            reset_config()
            config = get_config()

        project_paths = config.get_project_paths()
        themes_entries = self._normalize_theme_entries(config.get("themes_dir", []))
        if not themes_entries:
            console.print(
                f"[{COLOR.ERROR}]Error: No theme directory configured.[/{COLOR.ERROR}]"
            )
            return

        default_entries = self._normalize_theme_entries(
            ConfigManager.DEFAULT_CONFIG.get("themes_dir", [])
        )
        preferred_entries = [
            entry for entry in themes_entries if entry not in default_entries
        ]
        if not preferred_entries:
            preferred_entries = themes_entries

        themes_dir = self._resolve_theme_dir(
            preferred_entries[0], config.get_project_root()
        )
        themes_dir.mkdir(parents=True, exist_ok=True)

        base_name = Path(clean_name).name
        if base_name.endswith(".toml"):
            base_name = base_name[: -len(".toml")]
        if not base_name:
            console.print(
                f"[{COLOR.ERROR}]Error: Theme name cannot be empty.[/{COLOR.ERROR}]"
            )
            return

        target_file = themes_dir / f"{base_name}.toml"
        if target_file.exists():
            counter = 1
            while True:
                candidate = themes_dir / f"{base_name}_{counter}.toml"
                if not candidate.exists():
                    target_file = candidate
                    break
                counter += 1

        templates_dir = project_paths["templates_dir"]
        project_template_path = templates_dir / "theme.toml.j2"
        if project_template_path.exists():
            template_path = project_template_path
        else:
            template_path = TEMPLATES_DIR / "theme.toml.j2"

        template = Template(template_path.read_text())
        rendered_content = template.render()
        target_file.write_text(rendered_content)

        console.print(
            f"[{COLOR.SUCCESS}]Successfully created theme at {target_file}[/{COLOR.SUCCESS}]"
        )

    @staticmethod
    def _normalize_theme_entries(value: object) -> list[str]:
        if isinstance(value, str):
            normalized = value.strip()
            return [normalized] if normalized else []
        if isinstance(value, list):
            result: list[str] = []
            for entry in value:
                if not isinstance(entry, str):
                    continue
                normalized = entry.strip()
                if normalized:
                    result.append(normalized)
            return result
        return []

    @staticmethod
    def _resolve_theme_dir(entry: str, project_root: Path) -> Path:
        theme_path = Path(entry)
        if not theme_path.is_absolute():
            theme_path = project_root / theme_path
        return theme_path.resolve()
