"""Title display utilities for usecli CLI."""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, metadata
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # pragma: no cover - only on Python < 3.11

from rich.console import Console

from usecli.cli.config.colors import COLOR
from usecli.shared.config.manager import get_config

console = Console()


def _get_script_command_name(start_dir: Path | None = None) -> str | None:
    if start_dir is None:
        start_dir = Path.cwd()

    current = start_dir.resolve()

    while True:
        pyproject_path = current / "pyproject.toml"
        if pyproject_path.exists():
            try:
                data = tomllib.loads(pyproject_path.read_text())
            except (tomllib.TOMLDecodeError, OSError):
                data = {}

            scripts = data.get("project", {}).get("scripts", {})
            if isinstance(scripts, dict):
                for name, target in scripts.items():
                    if target == "usecli:main":
                        return name

        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


def get_script_command_name(default: str | None = None) -> str | None:
    config = get_config()
    config_command_name = config.get("command_name")
    if config.has_key("command_name") and config_command_name:
        return config_command_name

    command_name = _get_script_command_name(Path.cwd())
    if command_name:
        return command_name

    if config_command_name and config_command_name != "usecli":
        return config_command_name

    return default


def get_project_name() -> str:
    """Get the project name from config or package metadata."""
    # First, try to get the title from the config
    config = get_config()
    title = config.get("title")
    if config.has_key("title") and isinstance(title, str) and title.strip():
        normalized = title.strip()
        return "useCli" if normalized == "usecli" else normalized

    # Fall back to command name from pyproject.toml scripts
    command_name = _get_script_command_name(Path.cwd())
    if command_name:
        return "useCli" if command_name == "usecli" else command_name

    # Last resort: package metadata
    try:
        meta = metadata("usecli")
        name = meta.get("Name", "usecli")
        if name == "usecli":
            return "useCli"

        return name
    except PackageNotFoundError:
        return "useCli"


def get_figlet() -> Any | None:
    """Return the optional ``pyfiglet`` module, or None when it is not installed."""
    try:
        import pyfiglet
    except ImportError:
        return None
    return pyfiglet


def get_project_version() -> str | None:
    """Best-effort version of the running CLI.

    Resolves the distribution that owns the invoked console script first, then
    falls back to ``[project].version`` in the project's pyproject.toml.
    """
    command_name = get_script_command_name()
    if command_name:
        from usecli.shared.config.manager import _find_distribution_for_console_script

        dist = _find_distribution_for_console_script(command_name)
        if dist is not None:
            try:
                version = dist.version
            except (AttributeError, OSError, TypeError):
                version = None
            if version:
                return str(version)

    try:
        return get_config().get_project_version()
    except (AttributeError, OSError, ValueError):
        return None


def render_plain_title(
    title: str,
    description: str | None = None,
    version: str | None = None,
) -> str:
    """Render the non-figlet banner as Rich markup.

    The title and version share the first line in different colors; the
    description follows on the next line.
    """
    header = f"[bold {COLOR.PRIMARY}]{title}[/bold {COLOR.PRIMARY}]"
    if version:
        header += (
            f" [{COLOR.SECONDARY}]v{version.removeprefix('v')}[/{COLOR.SECONDARY}]"
        )
    if not description:
        return header
    return (
        f"{header}\n[{COLOR.FOREGROUND_MUTED}]{description}[/{COLOR.FOREGROUND_MUTED}]"
    )


def print_title(title: str | None = None) -> None:
    """Print the CLI banner.

    Uses figlet art when pyfiglet is installed; otherwise prints the title and
    version as colored text with the description on the next line.

    Args:
        title: Optional custom title text. If not provided, uses ASCII art.
    """
    default_title_text = """
                           ▄▄█▀▀▀▄█ ▀██   ██  
 ▄▄▄ ▄▄▄   ▄▄▄▄    ▄▄▄▄  ▄█▀     ▀   ██  ▄▄▄  
  ██  ██  ██▄ ▀  ▄█▄▄▄██ ██          ██   ██  
  ██  ██  ▄ ▀█▄▄ ██      ▀█▄      ▄  ██   ██  
  ▀█▄▄▀█▄ █▀▄▄█▀  ▀█▄▄▄▀  ▀▀█▄▄▄▄▀  ▄██▄ ▄██▄ 

 █████▓▓▓▓▓▒▒▒▒▒░░░░░░░░░░░░░░▒▒▒▒▒▓▓▓▓▓█████
        """
    config = get_config()

    title_extra_top_space = config.get("title_extra_top_space", False)
    title_extra_bottom_space = config.get("title_extra_bottom_space", False)

    if title_extra_top_space:
        console.print()

    title_file = config.get("title_file")
    if title_file:
        title_path = Path(title_file)
        if not title_path.is_absolute():
            title_path = config.get_project_root() / title_path
        try:
            if title_path.exists():
                title_text = title_path.read_text()
                console.print(f"[{COLOR.PRIMARY}]{title_text}")
                if title_extra_bottom_space:
                    console.print()
                return
        except OSError:
            pass

    if title is None or title.lower() == "usecli":
        console.print(f"[{COLOR.PRIMARY}]{default_title_text}")
        if title_extra_bottom_space:
            console.print()
        return

    figlet = get_figlet()
    title_font = config.get("title_font")
    if figlet is not None and title_font:
        try:
            raw_title = figlet.figlet_format(text=title, font=title_font).rstrip()
            title_text = "\n".join(" " + line for line in raw_title.split("\n"))
        except figlet.FontNotFound:
            title_text = title
        console.print(f"[{COLOR.PRIMARY}]{title_text}")
        if title_extra_bottom_space:
            console.print()
        return

    description = config.get("description") if config.has_key("description") else None
    console.print(render_plain_title(title, description, get_project_version()))
    if title_extra_bottom_space:
        console.print()
