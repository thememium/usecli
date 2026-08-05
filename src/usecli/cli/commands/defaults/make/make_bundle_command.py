"""MakeBundleCommand - build a PyInstaller bundle for the current project."""

from __future__ import annotations

import importlib.util
import os
import sys
from typing import Annotated

import typer
from rich.console import Console

from usecli.cli.config.colors import COLOR
from usecli.cli.core.base_command import BaseCommand
from usecli.menu import Menu
from usecli.ui import Confirm

console = Console()

_MODES = ("onefile", "onedir")

_MENU_LABEL_TO_MODE = {
    "One file (single executable)": "onefile",
    "One folder (bundle directory)": "onedir",
}


def _pyinstaller_available() -> bool:
    """True when PyInstaller (an optional dependency) is installed."""
    return importlib.util.find_spec("PyInstaller") is not None


class MakeBundleCommand(BaseCommand):
    """Build the current project into a standalone executable."""

    def visible(self) -> bool:
        command_name = os.path.basename(sys.argv[0]) if sys.argv else ""
        if command_name != "usecli":
            return False
        return _pyinstaller_available()

    def signature(self) -> str:
        return "make:bundle"

    def description(self) -> str:
        return "Build a standalone executable with PyInstaller"

    def handle(
        self,
        config_path: Annotated[
            str | None,
            typer.Argument(
                help="Path to usecli.config.toml (auto-detected when omitted)."
            ),
        ] = None,
        mode: Annotated[
            str | None,
            typer.Option(
                "--mode",
                "-m",
                help="onefile or onedir (interactive menu when omitted).",
            ),
        ] = None,
        name: Annotated[
            str | None,
            typer.Option("--name", help="Executable name override."),
        ] = None,
        distpath: Annotated[
            str | None,
            typer.Option("--distpath", help="Output directory for the bundle."),
        ] = None,
        workpath: Annotated[
            str | None,
            typer.Option("--workpath", help="PyInstaller work directory."),
        ] = None,
        yes: Annotated[
            bool,
            typer.Option(
                "--yes",
                "-y",
                help="Skip the confirmation prompt.",
            ),
        ] = False,
    ) -> None:
        """Handle the command execution."""
        if not _pyinstaller_available():
            console.print(
                f"[{COLOR.ERROR}]PyInstaller is required to build a bundle. "
                "Install it with `uv add usecli[pyinstaller]`.[/{COLOR.ERROR}]"
            )
            return
        if mode is None:
            choice = Menu.select(
                list(_MENU_LABEL_TO_MODE),
                title="Bundle type:",
            )
            if choice is None:
                console.print(f"[{COLOR.INFO}]Aborted.[/{COLOR.INFO}]")
                return
            mode = _MENU_LABEL_TO_MODE[choice]
        if mode not in _MODES:
            console.print(
                f"[{COLOR.ERROR}]Invalid mode {mode!r}; expected one of "
                f"{sorted(_MODES)}.[/{COLOR.ERROR}]"
            )
            return
        if not yes:
            confirmed = Confirm.ask(
                f"[{COLOR.WARNING}]Build a {mode} bundle with PyInstaller?[/{COLOR.WARNING}]",
                default=False,
            )
            if not confirmed:
                console.print(
                    f"[{COLOR.INFO}]Aborted. Re-run with --yes to skip confirmation.[/{COLOR.INFO}]"
                )
                return

        from usecli.bundler import pyinstaller

        pyinstaller(
            config_path=config_path,
            mode=mode,
            name=name,
            distpath=distpath,
            workpath=workpath,
        )
