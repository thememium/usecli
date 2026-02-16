"""Title display utilities for usecli CLI."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, metadata

from rich.console import Console

from usecli.cli.config.colors import COLOR

console = Console()


def get_project_name() -> str:
    """Get the project name from package metadata."""
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

        title_text = pyfiglet.figlet_format(text=title, font="big")
        console.print(f"[{COLOR.PRIMARY}]{title_text}")
    except (ImportError, ModuleNotFoundError):
        if title is None or title.lower() == "usecli":
            console.print(f"[{COLOR.PRIMARY}]{default_title_text}")
            return

        console.print(f"[{COLOR.PRIMARY}]{title}")
