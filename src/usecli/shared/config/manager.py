"""Configuration manager for useCli CLI.

Handles loading and accessing configuration from project-level files.
Configuration is loaded from (in priority order):
  1. pyproject.toml [tool.usecli] section (preferred for Python projects)
  2. usecli.config.toml (searched in current and parent directories)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from usecli.cli.core.exceptions.config import UsecliConfigError

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigManager:
    """Manages useCli configuration from project-level files.

    Configuration is loaded from:
    1. pyproject.toml [tool.usecli] in current directory (highest priority)
    2. usecli.config.toml (searched upward from current directory)
    3. Default values (lowest priority)

    Attributes:
        pyproject_path: Path to pyproject.toml in current directory.
        _config: The merged configuration dictionary.
    """

    DEFAULT_CONFIG: dict[str, Any] = {
        "title": "usecli",
        "description": "A customizable CLI framework",
        "show_setup": True,
        "commands_dir": "commands",
        "environment": "prod",
        "command_name": "usecli",
    }

    CONFIG_FILENAME = "usecli.config.toml"

    def __init__(
        self,
        pyproject_path: Path | None = None,
        start_dir: Path | None = None,
    ) -> None:
        """Initialize the configuration manager.

        Args:
            pyproject_path: Optional path to pyproject.toml. Defaults to
                ./pyproject.toml.
            start_dir: Optional directory to start searching for usecli.config.toml.
                Defaults to current working directory.
        """
        if pyproject_path is None:
            pyproject_path = Path.cwd() / "pyproject.toml"
        if start_dir is None:
            start_dir = Path.cwd()

        self.pyproject_path: Path = pyproject_path
        self.start_dir: Path = start_dir
        self._config: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load and merge configurations from all sources."""
        self._config = self.DEFAULT_CONFIG.copy()

        # Load usecli.config.toml from current or parent directories
        config_toml_path = self._find_config_toml()
        if config_toml_path:
            try:
                toml_config = self._load_toml(config_toml_path)
                self._config = _deep_merge(self._config, toml_config)
            except (tomllib.TOMLDecodeError, OSError) as e:
                raise UsecliConfigError(
                    f"Failed to load {self.CONFIG_FILENAME}: {e}",
                    config_file=str(config_toml_path),
                ) from e

        # pyproject.toml takes precedence over usecli.config.toml
        if self.pyproject_path.exists():
            try:
                pyproject_config = self._load_pyproject_toml(self.pyproject_path)
                if pyproject_config:
                    self._config = _deep_merge(self._config, pyproject_config)
            except (tomllib.TOMLDecodeError, OSError) as e:
                raise UsecliConfigError(
                    f"Failed to load pyproject.toml: {e}",
                    config_file=str(self.pyproject_path),
                ) from e

    def _find_config_toml(self) -> Path | None:
        """Find usecli.config.toml by searching upward from start_dir.

        Returns:
            Path to the found config file, or None if not found.
        """
        current = self.start_dir.resolve()

        while True:
            config_path = current / self.CONFIG_FILENAME
            if config_path.exists():
                return config_path

            # Stop at filesystem root
            parent = current.parent
            if parent == current:
                break
            current = parent

        return None

    @staticmethod
    def _load_toml(path: Path) -> dict[str, Any]:
        """Load TOML file and return [usecli] section.

        Args:
            path: Path to the TOML file.

        Returns:
            Parsed [usecli] section as a dictionary.
        """
        with open(path, "rb") as f:
            data = tomllib.load(f)
            return data.get("usecli", {})

    @staticmethod
    def _load_pyproject_toml(path: Path) -> dict[str, Any]:
        """Load pyproject.toml and return [tool.usecli] section.

        Args:
            path: Path to the pyproject.toml file.

        Returns:
            Parsed [tool.usecli] content as a dictionary, or empty dict.
        """
        with open(path, "rb") as f:
            data = tomllib.load(f)
            return data.get("tool", {}).get("usecli", {})

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation.

        Args:
            key: The configuration key in dot notation (e.g., "logging.level").
            default: Default value if key not found.

        Returns:
            The configuration value, or default if not found.
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if not isinstance(value, dict) or k not in value:
                return default
            value = value[k]
        return value

    def get_all(self) -> dict[str, Any]:
        """Get the complete merged configuration."""
        return self._config.copy()

    def is_dev(self) -> bool:
        """Check if running in development environment."""
        return self.get("environment", "prod") == "dev"

    def is_prod(self) -> bool:
        """Check if running in production environment."""
        return self.get("environment", "prod") == "prod"

    def reload(self) -> None:
        """Reload configuration from disk."""
        self._load_config()

    @property
    def pyproject_exists(self) -> bool:
        """Check if pyproject.toml with [tool.usecli] exists."""
        if not self.pyproject_path.exists():
            return False
        try:
            with open(self.pyproject_path, "rb") as f:
                data = tomllib.load(f)
                return "usecli" in data.get("tool", {})
        except (tomllib.TOMLDecodeError, OSError):
            return False

    @property
    def config_toml_path(self) -> Path | None:
        """Path to the found usecli.config.toml, or None."""
        return self._find_config_toml()


_config_manager: ConfigManager | None = None


def get_config() -> ConfigManager:
    """Get the global ConfigManager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def reset_config() -> None:
    """Reset the global ConfigManager instance."""
    global _config_manager
    _config_manager = None
