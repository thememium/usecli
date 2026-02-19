"""Command service for loading and managing CLI commands."""

from __future__ import annotations

import importlib.util
import inspect
import sys
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_version
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import typer

from usecli.cli.core.base_command import BaseCommand
from usecli.shared.config.globals import PACKAGE_ROOT
from usecli.shared.config.manager import get_config

if TYPE_CHECKING:
    pass


class CommandService:
    """Service for loading and managing CLI commands.

    This service dynamically discovers and loads command classes from
    the defaults and custom directories.
    """

    def __init__(self, app: typer.Typer) -> None:
        """Initialize the command service.

        Args:
            app: The Typer application instance.
        """
        self.app = app
        self.commands: list[str] = []
        self.version = "0.0.0"

    def load_commands(self) -> None:
        """Load all commands from the commands directory and project directories."""
        self._load_version()
        self._load_from_dir(PACKAGE_ROOT / "cli/commands")
        self._load_from_dir(get_config().get_project_commands_dir())

    def _load_version(self) -> None:
        """Load version from package metadata."""
        try:
            self.version = get_version("usecli")
        except PackageNotFoundError:
            self.version = "0.0.0"

    def _load_from_dir(self, directory: Path) -> None:
        """Load command classes from a directory.

        Args:
            directory: The directory to scan for Python files.
        """
        if not directory.exists():
            return

        for path in directory.rglob("*.py"):
            if path.name == "__init__.py":
                continue

            if "internal" in path.parts:
                continue

            module = self._import_file(path)
            if not module:
                continue

            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, BaseCommand)
                    and obj is not BaseCommand
                ):
                    obj(self.app)

    def _import_file(self, path: Path) -> ModuleType | None:
        """Import a Python file as a module.

        Args:
            path: Path to the Python file.

        Returns:
            The imported module, or None if import failed.
        """
        module_name = path.stem
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            return module
        return None
