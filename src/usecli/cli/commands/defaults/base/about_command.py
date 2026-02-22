from __future__ import annotations

import platform
import re
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_version
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from rich.console import Console

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.cli.core.ui.title import get_project_name
from usecli.shared.config.manager import ConfigManager, get_config

console = Console()


def _get_version() -> str:
    try:
        return get_version("usecli")
    except PackageNotFoundError:
        return "0.0.0"


def _parse_dependency_requirement(req: str) -> tuple[str, str | None]:
    req_core = req.split(";", 1)[0].strip()
    if not req_core:
        return "", None

    match = re.match(r"^([A-Za-z0-9_.-]+)", req_core)
    if not match:
        return "", None
    name = match.group(1)

    remainder = req_core[match.end() :].strip()
    if remainder.startswith("["):
        closing = remainder.find("]")
        if closing != -1:
            remainder = remainder[closing + 1 :].strip()

    if not remainder:
        return name, None

    if remainder.startswith("@"):
        spec = remainder[1:].strip()
        return name, spec or None

    return name, remainder


def _get_dependencies(config: ConfigManager) -> list[tuple[str, str | None]]:
    pyproject_path = config.pyproject_path
    if not pyproject_path.exists():
        return []

    try:
        data = tomllib.loads(pyproject_path.read_text())
    except (tomllib.TOMLDecodeError, OSError):
        return []

    deps = data.get("project", {}).get("dependencies", [])
    if not isinstance(deps, list):
        return []

    result: list[tuple[str, str | None]] = []
    for req in deps:
        if not isinstance(req, str):
            continue
        name, spec = _parse_dependency_requirement(req)
        if name and not req.startswith("("):
            result.append((name, spec))
    return result


def _get_script_commands() -> list[str]:
    pyproject_path = Path.cwd() / "pyproject.toml"
    if not pyproject_path.exists():
        return []

    try:
        data = tomllib.loads(pyproject_path.read_text())
    except (tomllib.TOMLDecodeError, OSError):
        return []

    scripts = data.get("project", {}).get("scripts", {})
    if not isinstance(scripts, dict):
        return []

    return [name for name in scripts.keys() if isinstance(name, str) and name.strip()]


class AboutCommand(BaseCommand):
    def signature(self) -> str:
        return "about"

    def description(self) -> str:
        return "Display detailed information about the application"

    def handle(self) -> None:
        config = get_config()
        version = config.get_project_version() or _get_version()
        app_name = get_project_name()
        description = config.get("description")
        if not (
            config.has_key("description")
            and isinstance(description, str)
            and description.strip()
        ):
            description = (
                "An elegant CLI framework for Python with prefix matching, "
                "rich UI, and command scaffolding."
            )
        description = description.strip() if isinstance(description, str) else ""

        console.print()
        console.print(f"[bold {COLOR.PRIMARY}]Description[/bold {COLOR.PRIMARY}]")
        console.print(f"[{COLOR.PRIMARY}]─" * 78)
        console.print(f"  {description}")

        console.print()
        console.print(f"[bold {COLOR.PRIMARY}]Environment[/bold {COLOR.PRIMARY}]")
        console.print(f"[{COLOR.PRIMARY}]─" * 78)

        self._print_row("Application Name", app_name)
        self._print_row("Application Version", version)
        self._print_row("Python Version", platform.python_version())
        self._print_row("Platform", f"[{COLOR.FOREGROUND_MUTED}]{platform.platform()}")

        console.print()
        console.print(f"[bold {COLOR.PRIMARY}]Entry Points[/bold {COLOR.PRIMARY}]")
        console.print(f"[{COLOR.PRIMARY}]─" * 78)

        script_commands = _get_script_commands() or ["usecli"]
        for index, command in enumerate(script_commands):
            label = "Primary command" if index == 0 else "Command"
            self._print_row(command, label)

        console.print()
        console.print(f"[bold {COLOR.PRIMARY}]Dependencies[/bold {COLOR.PRIMARY}]")
        console.print(f"[{COLOR.PRIMARY}]─" * 78)

        deps = _get_dependencies(config)
        if deps:
            for dep_name, spec in deps:
                if dep_name == "usecli" and spec:
                    self._print_row(dep_name, spec)
                    continue
                try:
                    installed_version = get_version(dep_name)
                    self._print_row(dep_name, installed_version)
                except Exception:
                    if spec:
                        self._print_row(dep_name, spec)
                    else:
                        self._print_row(dep_name, "not installed")
        else:
            self._print_row("Dependencies", "unable to load")

        # console.print()
        # console.print(f"[bold {COLOR.PRIMARY}]Features[/bold {COLOR.PRIMARY}]")
        # console.print(f"[{COLOR.PRIMARY}]─" * 78)
        #
        # self._print_row("Prefix Matching", f"[{COLOR.SECONDARY}]ENABLED")
        # self._print_row("Rich UI", f"[{COLOR.SECONDARY}]ENABLED")
        # self._print_row("Command Scaffolding", f"[{COLOR.SECONDARY}]ENABLED")
        # self._print_row("Interactive Menus", f"[{COLOR.SECONDARY}]ENABLED")
        # self._print_row("Fuzzy Finder", f"[{COLOR.SECONDARY}]ENABLED")
        console.print()

    def _print_row(self, label: str, value: str) -> None:
        visible_value = console.render_str(value).plain
        right_align_column = 76
        indent_width = 2
        padding_spaces = 2
        dots_length = (
            right_align_column
            - indent_width
            - len(label)
            - padding_spaces
            - len(visible_value)
        )
        dots = "." * max(dots_length, 1)
        console.print(
            f"  [{COLOR.FOREGROUND}]{label}[/{COLOR.FOREGROUND}] {dots} {value}"
        )
