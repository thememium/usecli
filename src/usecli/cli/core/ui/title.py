"""Title display utilities for usecli CLI."""

from __future__ import annotations

import os
import sys
import tomllib
from importlib.metadata import PackageNotFoundError, metadata
from pathlib import Path
from typing import Any

from rich.console import Console

from usecli.cli.config.colors import COLOR
from usecli.shared.config.manager import get_config

console = Console()

_FRAMEWORK_DIST_NAME = "usecli"

# argv0 values set by the interpreter rather than by a console script.
_NON_SCRIPT_ARGV0 = frozenset({"-c", "-m", "__main__.py"})


def _invoked_script_name() -> str | None:
    """Return the console-script name this process was started as."""
    if not sys.argv:
        return None
    name = os.path.basename(sys.argv[0])
    if not name or name in _NON_SCRIPT_ARGV0:
        return None
    return name


def _running_framework_distribution() -> Any | None:
    """Return the usecli distribution when running as one of its console scripts.

    The invoked console script decides the process identity: ``usecli`` (or
    ``usecli-bundle``) means the framework binary is running, so banners must
    describe the framework rather than the project it scaffolds.
    """
    script_name = _invoked_script_name()
    if script_name is None:
        return None

    from usecli.shared.config.manager import _find_distribution_for_console_script

    dist = _find_distribution_for_console_script(script_name)
    if dist is None:
        return None
    dist_name = dist.metadata.get("Name") or ""
    return dist if str(dist_name).strip().lower() == _FRAMEWORK_DIST_NAME else None


def _distribution_version(dist: Any) -> str | None:
    try:
        version = dist.version
    except (AttributeError, OSError, TypeError):
        return None
    return str(version) if version else None


def get_framework_description() -> str | None:
    """Description of the usecli distribution when running the framework binary.

    Returns ``None`` for downstream CLIs, whose config description owns the
    banner.
    """
    dist = _running_framework_distribution()
    if dist is None:
        return None
    summary = dist.metadata.get("Summary")
    summary = summary.strip() if isinstance(summary, str) else ""
    return summary or None


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
    """Get the command name used in usage lines and error messages.

    The usecli binary reports itself, not the project's CLI name: a user who
    typed ``usecli`` must see ``usecli`` in usage output.
    """
    if _running_framework_distribution() is not None:
        return "usecli"

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
    """Get the display name of the running CLI.

    The usecli binary reports the framework name; downstream CLIs report the
    title configured for their project.
    """
    if _running_framework_distribution() is not None:
        return "useCli"

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


def render_figlet_title(figlet: Any, text: str, font: str) -> str:
    """Render figlet art without blank rows above the glyphs.

    Some fonts (notably ``big`` with lowercase-only text) start with a
    whitespace-only row. That row is font layout, not intentional banner
    spacing; ``banner.top_space`` owns the banner's top spacing.
    """
    raw_title = figlet.figlet_format(text=text, font=font).rstrip()
    lines = raw_title.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(" " + line for line in lines)


def get_project_version() -> str | None:
    """Best-effort version of the running CLI.

    The usecli binary reports the installed framework version. A downstream
    CLI resolves the distribution that owns the invoked console script first,
    then falls back to ``[project].version`` in the project's pyproject.toml.
    """
    framework_dist = _running_framework_distribution()
    if framework_dist is not None:
        return _distribution_version(framework_dist)

    command_name = get_script_command_name()
    if command_name:
        from usecli.shared.config.manager import _find_distribution_for_console_script

        dist = _find_distribution_for_console_script(command_name)
        if dist is not None:
            version = _distribution_version(dist)
            if version:
                return version

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


def _print_banner_suffix(version: str | None, description: str | None) -> None:
    """Print the version and description lines that follow ASCII art."""
    if version:
        console.print(
            f" [{COLOR.SECONDARY}]v{version.removeprefix('v')}[/{COLOR.SECONDARY}]"
        )
    if description:
        console.print()
        console.print(
            f" [{COLOR.FOREGROUND_MUTED}]{description}[/{COLOR.FOREGROUND_MUTED}]"
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

    top_space = config.get("banner.top_space", True)
    bottom_space = config.get("banner.bottom_space", True)
    figlet = get_figlet()
    title_font = config.get("banner.font")
    show_description = (
        bool(config.get("banner.show_description"))
        if config.has_key("banner.show_description")
        else not (figlet is not None and bool(title_font))
    )
    framework_description = get_framework_description()
    if show_description and framework_description:
        description = framework_description
    else:
        description = (
            config.get("description")
            if show_description and config.has_key("description")
            else None
        )
    show_version = (
        bool(config.get("banner.show_version"))
        if config.has_key("banner.show_version")
        else not (figlet is not None and bool(title_font))
    )
    if top_space:
        console.print()

    title_file = config.get("banner.file")
    if title_file:
        title_path = Path(title_file)
        if not title_path.is_absolute():
            title_path = config.get_project_root() / title_path
        try:
            if title_path.exists():
                title_text = title_path.read_text().rstrip()
                console.print(f"[{COLOR.PRIMARY}]{title_text}")
                _print_banner_suffix(
                    get_project_version() if show_version else None,
                    description,
                )
                if bottom_space:
                    console.print()
                return
        except OSError:
            pass

    if title is None or title.lower() == "usecli":
        console.print(f"[{COLOR.PRIMARY}]{default_title_text}")
        if bottom_space:
            console.print()
        return

    version = get_project_version() if show_version else None
    if figlet is not None and title_font:
        try:
            title_text = render_figlet_title(figlet, title, title_font)
        except figlet.FontNotFound:
            title_text = title
        console.print(f"[{COLOR.PRIMARY}]{title_text}")
        _print_banner_suffix(version, description)
        if bottom_space:
            console.print()
        return

    console.print(render_plain_title(title, description, version))
    if bottom_space:
        console.print()
