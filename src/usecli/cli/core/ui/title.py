"""Title display utilities for usecli CLI."""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, metadata
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from rich.console import Console

from usecli.cli.config.colors import COLOR
from usecli.shared.config.manager import get_config

console = Console()


def _get_script_command_name() -> str | None:
    pyproject_path = Path.cwd() / "pyproject.toml"
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
        if target == "usecli:run_app":
            return name

    return None


def get_script_command_name(default: str | None = None) -> str | None:
    command_name = _get_script_command_name()
    if command_name:
        return command_name
    return default


def get_project_name() -> str:
    """Get the project name from config or package metadata."""
    # First, try to get the title from the config
    config = get_config()
    title = config.get("title")
    if title and title != "usecli":
        return title

    # Fall back to command name from pyproject.toml scripts
    command_name = get_script_command_name()
    if command_name:
        return "useCli" if command_name == "usecli" else command_name

    # Last resort: package metadata
    try:
        meta = metadata("usecli")
        name = meta["Name"] if "Name" in meta else "usecli"

        if name == "usecli":
            return "useCli"

        return name
    except PackageNotFoundError:
        return "useCli"


def print_title(title: str | None = None) -> None:
    """Print an ASCII art title, otherwise plain text.

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
    try:
        if title is None or title.lower() == "usecli":
            console.print(f"[{COLOR.PRIMARY}]{default_title_text}")
            return

        # Print Title using pyfiglet if available and non title is provided, otherwise print plain text
        import pyfiglet

        config = get_config()
        title_font = config.get("title_font", "big") or "big"
        try:
            raw_title = pyfiglet.figlet_format(text=title, font=title_font)
            title_text = "\n".join(" " + line for line in raw_title.split("\n"))
        except pyfiglet.FontNotFound:
            title_text = title
        console.print()
        console.print(f"[{COLOR.PRIMARY}]{title_text}")
    except (ImportError, ModuleNotFoundError):
        if title is None or title.lower() == "usecli":
            console.print(f"[{COLOR.PRIMARY}]{default_title_text}")
            return

        console.print(f"[{COLOR.PRIMARY}]{title}")
