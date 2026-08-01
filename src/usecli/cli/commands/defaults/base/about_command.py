from __future__ import annotations

import os
import sys
from importlib.metadata import PackageNotFoundError
from pathlib import Path

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.shared.config.manager import get_config


class _LazyConsole:
    _console = None

    def _get_console(self):
        if self._console is None:
            from rich.console import Console

            self._console = Console()
        return self._console

    def __getattr__(self, name):
        return getattr(self._get_console(), name)


console = _LazyConsole()


def _load_toml(text: str):
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib

    return tomllib.loads(text)


def _toml_decode_error():
    if sys.version_info >= (3, 11):
        pass
    else:
        pass

    return _toml_decode_error()


def _get_version() -> str:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as get_version

    try:
        return get_version("usecli")
    except PackageNotFoundError:
        return "0.0.0"


def _parse_dependency_requirement(req: str) -> tuple[str, str | None]:
    req_core = req.split(";", 1)[0].strip()
    if not req_core:
        return "", None

    import re

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


def _get_console_script_distribution(command_name: str | None):
    if not command_name:
        return None
    from usecli.shared.config.manager import _find_distribution_for_console_script

    return _find_distribution_for_console_script(command_name)


def _get_package_dependencies_from_distribution(dist) -> list[tuple[str, str | None]]:
    requires = dist.requires or []
    result: list[tuple[str, str | None]] = []
    for req in requires:
        if not isinstance(req, str):
            continue
        name, spec = _parse_dependency_requirement(req)
        if name and not req.startswith("("):
            result.append((name, spec))
    return result


def _get_dependencies(config) -> list[tuple[str, str | None]]:
    command_name = os.path.basename(sys.argv[0]) if sys.argv else None
    dist = _get_console_script_distribution(command_name)
    if dist is None:
        from usecli.cli.core.ui.title import get_script_command_name

        primary_command = get_script_command_name(default=None)
        dist = _get_console_script_distribution(primary_command)
    if dist is not None:
        return _get_package_dependencies_from_distribution(dist)

    pyproject_path = config.pyproject_path
    if not pyproject_path.exists():
        return []

    try:
        data = _load_toml(pyproject_path.read_text())
    except (_toml_decode_error(), OSError):
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


def _get_application_distribution():
    command_name = os.path.basename(sys.argv[0]) if sys.argv else None
    dist = _get_console_script_distribution(command_name)
    if dist is None:
        from usecli.cli.core.ui.title import get_script_command_name

        primary_command = get_script_command_name(default=None)
        dist = _get_console_script_distribution(primary_command)
    return dist


def _get_application_version(config) -> str:
    dist = _get_application_distribution()
    if dist is not None:
        return dist.version

    config_version = config.get_project_version()
    if config_version:
        return config_version

    return _get_version()


def _get_application_description(config) -> str:
    description = config.get("description")
    if (
        config.has_key("description")
        and isinstance(description, str)
        and description.strip()
    ):
        return description.strip()

    project_description = _get_project_description(config)
    if project_description:
        return project_description

    return (
        "An elegant CLI framework for Python with prefix matching, "
        "rich UI, and command scaffolding."
    )


def _get_project_description(config) -> str | None:
    pyproject_path = config.pyproject_path
    if not pyproject_path.exists():
        return None

    try:
        data = _load_toml(pyproject_path.read_text())
    except (_toml_decode_error(), OSError):
        return None

    description = data.get("project", {}).get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()
    return None


def _get_installed_script_commands(command_name: str | None) -> list[str]:
    dist = _get_console_script_distribution(command_name)
    if dist is None:
        return []
    try:
        entry_points = dist.entry_points
    except (AttributeError, OSError):
        return []
    script_names = [
        entry_point.name
        for entry_point in entry_points
        if entry_point.group == "console_scripts"
    ]
    if not script_names:
        return []
    if command_name and command_name in script_names:
        return [command_name, *[name for name in script_names if name != command_name]]
    return script_names


def _get_script_commands() -> list[str]:
    from usecli.cli.core.ui.title import get_script_command_name

    primary_command = get_script_command_name(default=None)
    command_name = os.path.basename(sys.argv[0]) if sys.argv else primary_command
    installed_commands = _get_installed_script_commands(command_name)
    if installed_commands:
        if primary_command and primary_command not in installed_commands:
            return [primary_command, *installed_commands]
        return installed_commands

    pyproject_path = Path.cwd() / "pyproject.toml"
    if not pyproject_path.exists():
        if primary_command:
            return [primary_command]
        return []

    try:
        data = _load_toml(pyproject_path.read_text())
    except (_toml_decode_error(), OSError):
        return []

    scripts = data.get("project", {}).get("scripts", {})
    if not isinstance(scripts, dict):
        if primary_command:
            return [primary_command]
        return []

    script_names = [
        name for name in scripts if isinstance(name, str) and name.strip()
    ]
    if primary_command and primary_command not in script_names:
        return [primary_command, *script_names]
    return script_names


class AboutCommand(BaseCommand):
    def signature(self) -> str:
        return "about"

    def description(self) -> str:
        return "Display detailed information about the application"

    def handle(self) -> dict[str, object]:
        import platform

        config = get_config()
        version = _get_application_version(config)
        from usecli.cli.core.ui.title import get_project_name

        app_name = get_project_name()
        description = _get_application_description(config)

        dist = _get_application_distribution()
        name_label = "Cli Name" if dist is not None else "Application Name"
        version_label = "Cli Version" if dist is not None else "Application Version"

        script_commands = _get_script_commands() or ["usecli"]

        deps = _get_dependencies(config)
        dependencies: list[dict[str, str | None]] = []
        for dep_name, spec in deps:
            try:
                from importlib.metadata import version as get_version

                installed_version = get_version(dep_name)
                dependencies.append({"name": dep_name, "version": installed_version})
            except (PackageNotFoundError, OSError):
                dependencies.append({"name": dep_name, "version": spec})

        data: dict[str, object] = {
            "name": app_name,
            "version": version,
            "description": description,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "entry_points": script_commands,
            "dependencies": dependencies,
        }

        from usecli.cli.core.runtime import is_json_mode

        if is_json_mode():
            return data

        console.print()
        console.print(f"[bold {COLOR.PRIMARY}]Description[/bold {COLOR.PRIMARY}]")
        console.print(f"[{COLOR.PRIMARY}]─" * 78)
        console.print(f"  {description}")

        console.print()
        console.print(f"[bold {COLOR.PRIMARY}]Environment[/bold {COLOR.PRIMARY}]")
        console.print(f"[{COLOR.PRIMARY}]─" * 78)
        self._print_row(name_label, app_name)
        self._print_row(version_label, version)
        self._print_row("Python Version", platform.python_version())
        self._print_row("Platform", f"[{COLOR.FOREGROUND_MUTED}]{platform.platform()}")

        console.print()
        console.print(f"[bold {COLOR.PRIMARY}]Entry Points[/bold {COLOR.PRIMARY}]")
        console.print(f"[{COLOR.PRIMARY}]─" * 78)
        for index, command in enumerate(script_commands):
            label = "Primary command" if index == 0 else "Command"
            self._print_row(command, label)

        console.print()
        console.print(f"[bold {COLOR.PRIMARY}]Dependencies[/bold {COLOR.PRIMARY}]")
        console.print(f"[{COLOR.PRIMARY}]─" * 78)
        if deps:
            for dep_name, spec in deps:
                try:
                    from importlib.metadata import version as get_version

                    installed_version = get_version(dep_name)
                    self._print_row(dep_name, installed_version)
                except (PackageNotFoundError, OSError):
                    if spec:
                        self._print_row(dep_name, spec)
                    else:
                        self._print_row(dep_name, "not installed")
        else:
            self._print_row("Dependencies", "unable to load")

        console.print()

        return data

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
