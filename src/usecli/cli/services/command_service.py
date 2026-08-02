"""Command service for loading and managing CLI commands."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import typer

from usecli.cli.core.base_command import BaseCommand
from usecli.shared.config.globals import PACKAGE_ROOT


def get_config():
    """Lazy wrapper around manager.get_config for test mocking compatibility."""
    from usecli.shared.config.manager import get_config as _get_config

    return _get_config()


def get_version(package_name: str) -> str:
    from importlib.metadata import version

    return version(package_name)


def _is_package_not_found(error: Exception) -> bool:
    return error.__class__.__name__ == "PackageNotFoundError"


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
        self._skip_usecli_only_commands = False

    def load_commands(self) -> None:
        """Load all commands from the commands directory and project directories."""
        self._load_version()
        config = get_config()

        command_name = Path(sys.argv[0]).name if sys.argv else ""
        if config.is_usecli_direct_dependency():
            package_commands_dir = (PACKAGE_ROOT / "cli/commands").resolve()
            self._skip_usecli_only_commands = command_name != "usecli"
            try:
                self._load_from_dir(package_commands_dir)
            finally:
                self._skip_usecli_only_commands = False

        project_commands_dir = config.get_project_commands_dir().resolve()
        package_commands_dir = (PACKAGE_ROOT / "cli/commands").resolve()
        if project_commands_dir == package_commands_dir:
            return
        try:
            project_commands_dir.relative_to(package_commands_dir)
            return
        except ValueError:
            self._load_from_dir(project_commands_dir)

    def _load_version(self) -> None:
        # Try the installed distribution first, same order as
        # about_command.py's _get_application_version(). A pyproject.toml
        # walked up from cwd has no ownership check - it can belong to an
        # unrelated project the user happens to be standing in - so it's
        # only a fallback, not the first check.
        app_version = self._get_application_version()
        if app_version:
            self.version = app_version
            return
        config_version = get_config().get_project_version()
        if config_version:
            self.version = config_version
            return
        try:
            self.version = get_version("usecli")
        except Exception as error:
            if not _is_package_not_found(error):
                raise
            self.version = "0.0.0"

    def _get_application_version(self) -> str | None:
        """Get the version from the application's own distribution.

        Finds the distribution that registered the current console script
        (e.g., 'usepr') and returns its version, so user-built CLIs
        show their own version instead of usecli's.
        """
        import os

        from usecli.cli.core.ui.title import get_script_command_name
        from usecli.shared.config.manager import _find_distribution_for_console_script

        command_name = os.path.basename(sys.argv[0]) if sys.argv else None
        if command_name:
            dist = _find_distribution_for_console_script(command_name)
            if dist is not None:
                return dist.version
        primary_command = get_script_command_name(default=None)
        if primary_command:
            dist = _find_distribution_for_console_script(primary_command)
            if dist is not None:
                return dist.version
        return None

    def _load_from_dir(self, directory: Path) -> None:
        """Load command classes from a directory.

        Args:
            directory: The directory to scan for Python files.
        """
        if not directory.exists():
            return

        skip_usecli_only = self._skip_usecli_only_commands

        for path in directory.rglob("*.py"):
            if path.name == "__init__.py":
                continue

            if skip_usecli_only and (
                path.name == "init_command.py" or path.parent.name == "make"
            ):
                continue

            if "internal" in path.parts:
                continue

            module = self._import_file(path)
            if module is None:
                continue

            if isinstance(module, ModuleType):
                members = module.__dict__.values()

                def is_command_class(obj: object) -> bool:
                    return isinstance(obj, type)
            else:
                import inspect

                members = (obj for _, obj in inspect.getmembers(module))
                is_command_class = inspect.isclass

            for obj in members:
                if (
                    is_command_class(obj)
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

            from usecli.shared.config.manager import find_project_root

            project_root = find_project_root(path.parent)
            if project_root and str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            spec.loader.exec_module(module)
            return module
        return None
