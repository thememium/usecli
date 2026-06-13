"""Title display utilities for usecli CLI."""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def _lazy_console():
    from rich.console import Console
    return Console()


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
    from usecli.shared.config.manager import get_config
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
    from usecli.shared.config.manager import get_config

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
        from importlib.metadata import PackageNotFoundError, metadata

        meta = metadata("usecli")
        name = meta["Name"] if "Name" in meta else "usecli"

        if name == "usecli":
            return "useCli"

        return name
    except (PackageNotFoundError, Exception):
        return "useCli"


def print_title(title: str | None = None) -> None:
    """Print an ASCII art title, otherwise plain text.

    Args:
        title: Optional custom title text. If not provided, uses ASCII art.
    """
    from usecli.cli.config.colors import COLOR
    from usecli.shared.config.manager import get_config

    console = _lazy_console()

    default_title_text = """
                           ▄▄█▀▀▀▄█ ▀██   ██  
 ▄▄▄ ▄▄▄   ▄▄▄▄    ▄▄▄▄  ▄█▀     ▀   ██  ▄▄▄  
  ██  ██  ██▄ ▀  ▄█▄▄▄██ ██          ██   ██  
  ██  ██  ▄ ▀█▄▄ ██      ▀█▄      ▄  ██   ██  
  ▀█▄▄▀█▄ █▀▄▄█▀  ▀█▄▄▄▀  ▀▀█▄▄▄▄▀  ▄██▄ ▄██▄ 

 █████▓▓▓▓▓▒▒▒▒▒░░░░░░░░░░░░░░▒▒▒▒▒▓▓▓▓▓█████
        """
    config = get_config()

    title_file = config.get("title_file")
    if title_file:
        title_path = Path(title_file)
        if not title_path.is_absolute():
            title_path = config.get_project_root() / title_path
        try:
            if title_path.exists():
                title_text = title_path.read_text()
                console.print()
                console.print(f"[{COLOR.PRIMARY}]{title_text}")
                return
        except OSError:
            pass

    try:
        if title is None or title.lower() == "usecli":
            console.print(f"[{COLOR.PRIMARY}]{default_title_text}")
            return

        # Print Title using pyfiglet if available and non title is provided, otherwise print plain text
        import pyfiglet

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
