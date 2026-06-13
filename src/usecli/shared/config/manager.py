"""Configuration manager for useCli CLI.

Handles loading and accessing configuration from project-level files.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

from usecli.shared.config.globals import PYPROJECT_TOML, USECLI_CONFIG_TOML

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# Depth cap for rglob – prevents scanning massive trees like ~/ghq.
_MAX_RGLOB_DEPTH = 6

# High-level directories that should never be recursively searched for configs.
# Searching HOME or filesystem roots is extremely expensive and will never find
# a project-specific config.
HIGH_LEVEL_DIRS: frozenset[str] = frozenset(
    {
        str(Path.home().resolve()),
        "/",
        "/Users",
        "/home",
        "/root",
        "/tmp",
        "/var",
        "/etc",
        "/usr",
    }
)

# Cache for config search results to avoid repeated expensive searches.
_config_search_cache: dict[str, Path | None] = {}

_WALK_SKIP_ALWAYS: frozenset[str] = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".auto",
        ".eggs",
        "*.egg-info",
    }
)

_WALK_SKIP_VENV: frozenset[str] = frozenset(
    {
        ".venv",
        "venv",
        "site-packages",
        "dist-packages",
        "__pypackages__",
        "pipx",
        "venvs",
    }
)


def _walk_for_filename(
    directory: Path,
    filename: str,
    depth: int,
    max_depth: int,
    skip_dirs: frozenset[str],
    results: list[Path],
) -> None:
    if depth > max_depth:
        return
    try:
        entries = list(directory.iterdir())
    except (PermissionError, OSError):
        return
    for entry in entries:
        try:
            if entry.is_file() and entry.name == filename:
                results.append(entry)
            elif entry.is_dir() and entry.name not in skip_dirs:
                _walk_for_filename(
                    entry, filename, depth + 1, max_depth, skip_dirs, results
                )
        except (PermissionError, OSError):
            continue


def _rglob_limited(
    root_dir: Path,
    filename: str,
    *,
    skip_venv: bool = True,
    max_depth: int = _MAX_RGLOB_DEPTH,
) -> list[Path]:
    """Depth-bounded recursive filename search that prunes dirs during the walk."""
    skip_dirs = _WALK_SKIP_ALWAYS | _WALK_SKIP_VENV if skip_venv else _WALK_SKIP_ALWAYS
    results: list[Path] = []
    _walk_for_filename(root_dir, filename, 0, max_depth, skip_dirs, results)
    return results


def _get_importlib_metadata():
    import importlib.metadata

    return importlib.metadata


_distributions_cache: list[Any] | None = None


def _get_distributions() -> list[Any]:
    global _distributions_cache
    if _distributions_cache is not None:
        return _distributions_cache
    try:
        metadata = _get_importlib_metadata()
        _distributions_cache = list(metadata.distributions())
    except Exception:
        _distributions_cache = []
    return _distributions_cache


def _reset_distributions_cache() -> None:
    global _distributions_cache
    _distributions_cache = None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _normalize_themes_dir(value: Any) -> list[str]:
    if isinstance(value, str):
        normalized = value.strip()
        return [normalized] if normalized else []
    if isinstance(value, list):
        result: list[str] = []
        for entry in value:
            if not isinstance(entry, str):
                continue
            normalized = entry.strip()
            if normalized:
                result.append(normalized)
        return result
    return []


def _dedupe_items(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


class ConfigManager:
    """Manages useCli configuration from project-level files."""

    _SKIP_DIRS = {
        ".venv",
        "venv",
        "site-packages",
        "dist-packages",
        "__pypackages__",
        "pipx",
        "venvs",
    }

    DEFAULT_CONFIG: dict[str, Any] = {
        "title": "usecli",
        "title_file": None,
        "description": "A customizable CLI framework",
        "commands_dir": "cli/commands",
        "templates_dir": "cli/templates",
        "themes_dir": ["cli/themes"],
        "title_font": "big",
        "theme": "default",
        "environment": "prod",
        "command_name": "usecli",
        "hide_inspire": False,
    }

    def __init__(
        self,
        pyproject_path: Path | None = None,
        usecli_config_path: Path | None = None,
        start_dir: Path | None = None,
    ) -> None:
        """Initialize the configuration manager.

        Args:
            pyproject_path: Optional path to pyproject.toml. Defaults to
                ./pyproject.toml.
            start_dir: Optional directory to start searching for pyproject.toml.
                Defaults to current working directory.
        """
        if start_dir is None:
            start_dir = Path.cwd()

        if pyproject_path is None:
            pyproject_path = self._find_pyproject_toml(start_dir) or (
                start_dir / PYPROJECT_TOML
            )

        if usecli_config_path is None:
            usecli_config_path = self._find_usecli_config(start_dir) or (
                start_dir / USECLI_CONFIG_TOML
            )

        self.pyproject_path: Path = pyproject_path
        self.usecli_config_path: Path = usecli_config_path
        self.start_dir: Path = start_dir
        detected_root = find_project_root(start_dir)
        if self.usecli_config_path.exists():
            config_parent = self.usecli_config_path.parent
            if detected_root is None:
                detected_root = config_parent
            else:
                root_config = detected_root / USECLI_CONFIG_TOML
                if self.usecli_config_path.resolve() != root_config.resolve():
                    detected_root = config_parent
                else:
                    try:
                        self.usecli_config_path.relative_to(detected_root)
                    except ValueError:
                        detected_root = config_parent
                    else:
                        if any(
                            part in self._SKIP_DIRS
                            for part in self.usecli_config_path.parts
                        ):
                            detected_root = config_parent
        self.project_root: Path = (detected_root or start_dir).resolve()
        # Only override project_root for the framework itself (usecli).
        # Downstream packages (usechange, userun, etc.) legitimately live
        # inside .venv when installed as dependencies — don't break them.
        command_name = self._get_command_name()
        is_framework = command_name == "usecli" if command_name else True
        if is_framework and self._is_in_venv(self.project_root):
            self.project_root = start_dir.resolve()
        self._config: dict[str, Any] = {}
        self._overrides: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load and merge configurations from all sources."""
        self._config = self.DEFAULT_CONFIG.copy()
        self._overrides = {}

        if self.usecli_config_path.exists():
            try:
                usecli_config = self._load_usecli_toml(self.usecli_config_path)
                if usecli_config:
                    self._config = _deep_merge(self._config, usecli_config)
                    self._overrides = _deep_merge(self._overrides, usecli_config)
            except (tomllib.TOMLDecodeError, OSError) as e:
                from usecli.cli.core.exceptions.config import UsecliConfigError

                raise UsecliConfigError(
                    f"Failed to load {USECLI_CONFIG_TOML}: {e}",
                    config_file=str(self.usecli_config_path),
                ) from e

        default_themes = _normalize_themes_dir(self.DEFAULT_CONFIG.get("themes_dir"))
        override_themes = _normalize_themes_dir(self._overrides.get("themes_dir"))
        merged_themes = _dedupe_items(default_themes + override_themes)
        if merged_themes:
            self._config["themes_dir"] = merged_themes

    @staticmethod
    def _pyproject_has_usecli(path: Path) -> bool:
        if not path.exists():
            return False
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
                return "usecli" in data.get("tool", {})
        except (tomllib.TOMLDecodeError, OSError):
            return False

    @classmethod
    def _find_pyproject_toml(cls, start_dir: Path) -> Path | None:
        current = start_dir.resolve()

        while True:
            pyproject_path = current / PYPROJECT_TOML
            if pyproject_path.exists():
                return pyproject_path

            parent = current.parent
            if parent == current:
                break
            current = parent

        return None

    @classmethod
    def _find_usecli_config(cls, start_dir: Path) -> Path | None:
        current = start_dir.resolve()
        command_name = cls._get_command_name()

        while True:
            config_path = current / USECLI_CONFIG_TOML
            if config_path.exists() and cls._config_matches_command(
                config_path, command_name
            ):
                return config_path

            parent = current.parent
            if parent == current:
                break
            current = parent

        # Try fast lookups before expensive rglob (perf: global tools).
        console_match = cls._find_usecli_config_for_console_script()
        if console_match:
            return console_match

        if cls._is_within_usecli_package(start_dir):
            package_match = cls._find_usecli_config_in_package()
            if package_match:
                return package_match

            sys_match = cls._find_usecli_config_on_sys_path()
            if sys_match:
                return sys_match

        # Check cache first to avoid repeated expensive searches.
        cache_key = str(start_dir.resolve())
        if cache_key in _config_search_cache:
            return _config_search_cache[cache_key]

        search_root = find_project_root(start_dir) or start_dir.resolve()

        # Skip expensive recursive search when search root is a high-level directory.
        # Global tools running from HOME or / will never find a project config this way.
        if str(search_root) in HIGH_LEVEL_DIRS:
            _config_search_cache[cache_key] = None
            return None

        is_framework = command_name == "usecli" if command_name else True
        recursive_match = cls._find_usecli_config_in_tree(
            search_root, start_dir, skip_venv=is_framework
        )
        _config_search_cache[cache_key] = recursive_match
        if recursive_match:
            return recursive_match

        return None

    @staticmethod
    def _find_usecli_config_in_tree(
        root_dir: Path, start_dir: Path, *, skip_venv: bool
    ) -> Path | None:
        if not root_dir.exists() or not root_dir.is_dir():
            return None

        candidates = _rglob_limited(root_dir, USECLI_CONFIG_TOML, skip_venv=skip_venv)
        command_name = ConfigManager._get_command_name()
        if command_name:
            candidates = [
                path
                for path in candidates
                if ConfigManager._config_matches_command(path, command_name)
            ]
        if not candidates:
            return None

        start_dir = start_dir.resolve()
        preferred: list[Path] = []
        for path in candidates:
            try:
                path.relative_to(start_dir)
                preferred.append(path)
            except ValueError:
                continue

        selection = preferred or candidates

        def _depth_key(path: Path) -> tuple[int, str]:
            try:
                relative = path.relative_to(start_dir)
                return (len(relative.parts), str(path))
            except ValueError:
                relative = path.relative_to(root_dir)
                return (len(relative.parts), str(path))

        selection.sort(key=_depth_key)
        return selection[0]

    @staticmethod
    def _find_usecli_config_in_package() -> Path | None:
        package_name = _get_package_name()
        spec = importlib.util.find_spec(package_name)
        if spec is None or not spec.submodule_search_locations:
            return None

        command_name = ConfigManager._get_command_name()

        try:
            metadata = _get_importlib_metadata()
            dist = metadata.distribution(package_name)
            source_root = ConfigManager._resolve_editable_source_root(dist)
            if source_root:
                source_config = ConfigManager._search_source_for_config(
                    source_root, command_name, None
                )
                if source_config:
                    return source_config
        except Exception:
            pass

        for location in spec.submodule_search_locations:
            package_root = Path(location)
            if not package_root.exists() or not package_root.is_dir():
                continue
            candidates = _rglob_limited(
                package_root, USECLI_CONFIG_TOML, skip_venv=False
            )
            if command_name:
                candidates = [
                    path
                    for path in candidates
                    if ConfigManager._config_matches_command(path, command_name)
                ]
            if candidates:
                candidates.sort(key=lambda path: (len(path.parts), str(path)))
                return candidates[0]
        return None

    @classmethod
    def _find_usecli_config_in_named_package(cls, package_name: str) -> Path | None:
        if not package_name:
            return None
        spec = importlib.util.find_spec(package_name)
        if spec is None or not spec.submodule_search_locations:
            return None

        command_name = cls._get_command_name()

        try:
            metadata = _get_importlib_metadata()
            dist = metadata.distribution(package_name)
            source_root = cls._resolve_editable_source_root(dist)
            if source_root:
                source_config = cls._search_source_for_config(
                    source_root, command_name, None
                )
                if source_config:
                    return source_config
        except Exception:
            pass

        for location in spec.submodule_search_locations:
            package_root = Path(location)
            if not package_root.exists() or not package_root.is_dir():
                continue
            candidates = _rglob_limited(
                package_root, USECLI_CONFIG_TOML, skip_venv=False
            )
            if command_name:
                candidates = [
                    path
                    for path in candidates
                    if cls._config_matches_command(path, command_name)
                ]
            if candidates:
                candidates.sort(key=lambda path: (len(path.parts), str(path)))
                return candidates[0]
        return None

    @classmethod
    def _find_usecli_config_for_console_script(cls) -> Path | None:
        command_name = os.path.basename(sys.argv[0]) if sys.argv else ""
        if not command_name:
            return None
        distributions = _get_distributions()
        for dist in distributions:
            try:
                entry_points = dist.entry_points
            except Exception:
                continue
            for entry_point in entry_points:
                if entry_point.group != "console_scripts":
                    continue
                if entry_point.name != command_name:
                    continue
                metadata = dist.metadata
                dist_name = ""
                if "Name" in metadata:
                    dist_name = metadata["Name"]
                elif "name" in metadata:
                    dist_name = metadata["name"]
                candidates = []
                if dist_name:
                    candidates.append(dist_name)
                    normalized = dist_name.replace("-", "_")
                    if normalized not in candidates:
                        candidates.append(normalized)
                aliases = cls._get_console_script_aliases(command_name)
                for package_name in candidates:
                    source_root = cls._resolve_editable_source_root(dist)
                    if source_root:
                        source_config = cls._search_source_for_config(
                            source_root, command_name, aliases
                        )
                        if source_config:
                            return source_config
                    match = cls._find_usecli_config_in_named_package(package_name)
                    if match:
                        return match
        return None

    @staticmethod
    def _is_preferred_package_path(path: Path) -> bool:
        return any(part in ConfigManager._SKIP_DIRS for part in path.parts)

    @staticmethod
    def _is_within_usecli_package(start_dir: Path) -> bool:
        spec = importlib.util.find_spec(_get_package_name())
        if spec is None or not spec.submodule_search_locations:
            return False
        start_dir = start_dir.resolve()
        for location in spec.submodule_search_locations:
            package_root = Path(location)
            try:
                start_dir.relative_to(package_root)
                return True
            except ValueError:
                continue
        return False

    @staticmethod
    def _find_usecli_config_on_sys_path() -> Path | None:
        for entry in sys.path:
            if not entry:
                continue
            path = Path(entry)
            if not path.exists() or not path.is_dir():
                continue
            candidate = path / USECLI_CONFIG_TOML
            if candidate.exists():
                return candidate
            for child in path.glob(f"*/{USECLI_CONFIG_TOML}"):
                if child.exists():
                    return child
        return None

    @staticmethod
    def _load_usecli_toml(path: Path) -> dict[str, Any]:
        with open(path, "rb") as f:
            data = tomllib.load(f)

        tool_section = data.get("tool", {})
        if isinstance(tool_section, dict) and "usecli" in tool_section:
            usecli_section = tool_section.get("usecli")
            if isinstance(usecli_section, dict):
                return usecli_section

        usecli_section = data.get("usecli", {})
        if isinstance(usecli_section, dict):
            return usecli_section

        return {}

    @staticmethod
    def _get_command_name() -> str | None:
        if not sys.argv:
            return None
        command = os.path.basename(sys.argv[0])
        return command if command else None

    @staticmethod
    def _get_console_script_aliases(command_name: str | None) -> set[str]:
        if not command_name:
            return set()
        aliases: set[str] = {command_name}
        distributions = _get_distributions()
        for dist in distributions:
            try:
                entry_points = dist.entry_points
            except Exception:
                continue
            names = [
                entry_point.name
                for entry_point in entry_points
                if entry_point.group == "console_scripts"
            ]
            if command_name in names:
                aliases.update(names)
                break
        return aliases

    @staticmethod
    def _config_matches_command(
        path: Path, command_name: str | None, aliases: set[str] | None = None
    ) -> bool:
        if command_name is None:
            return True
        try:
            config = ConfigManager._load_usecli_toml(path)
        except (tomllib.TOMLDecodeError, OSError):
            return True
        config_command = config.get("command_name")
        if not isinstance(config_command, str):
            return True
        normalized = config_command.strip()
        if not normalized:
            return True
        if normalized == command_name:
            return True
        if aliases is None:
            aliases = ConfigManager._get_console_script_aliases(command_name)
        return normalized in aliases

    @staticmethod
    def _is_in_venv(path: Path) -> bool:
        resolved = path.resolve()
        return any(part in ConfigManager._SKIP_DIRS for part in resolved.parts)

    @staticmethod
    def _resolve_editable_source_root(
        dist: Any,
    ) -> Path | None:
        """Resolve the source directory for an editable-installed package.

        Reads ``direct_url.json`` from the distribution's metadata to find the
        local source tree.  Returns the source root or ``None`` when the
        distribution is not an editable install or the source no longer exists.
        """
        try:
            text = dist.read_text("direct_url.json")
        except Exception:
            return None
        if not text:
            return None
        import json

        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(data, dict):
            return None
        if data.get("dir_info", {}).get("editable") is not True:
            return None
        url = data.get("url", "")
        if not url:
            return None
        # ``url`` is a ``file://`` URI.
        if url.startswith("file://"):
            url = url[len("file://") :]
        source = Path(url)
        if source.exists() and source.is_dir():
            return source.resolve()
        return None

    @staticmethod
    def _search_source_for_config(
        source_root: Path,
        command_name: str | None,
        aliases: set[str] | None,
    ) -> Path | None:
        """Search a source tree for a ``usecli.config.toml`` that matches."""
        if not source_root.exists() or not source_root.is_dir():
            return None
        candidates = _rglob_limited(source_root, USECLI_CONFIG_TOML)
        if command_name:
            candidates = [
                p
                for p in candidates
                if ConfigManager._config_matches_command(p, command_name, aliases)
            ]
        if not candidates:
            return None
        candidates.sort(key=lambda p: (len(p.parts), str(p)))
        return candidates[0]

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

    def has_key(self, key: str) -> bool:
        keys = key.split(".")
        value: Any = self._overrides
        for k in keys:
            if not isinstance(value, dict) or k not in value:
                return False
            value = value[k]
        return True

    def get_project_root(self) -> Path:
        return self.project_root

    def get_project_version(self) -> str | None:
        pyproject_version = self._load_project_version(self.pyproject_path)
        if pyproject_version:
            return pyproject_version
        return None

    def get_project_commands_dir(self) -> Path:
        commands_dir = self.get("commands_dir", "cli/commands")
        commands_path = Path(commands_dir)
        if commands_path.is_absolute():
            return commands_path
        # Resolve relative to the config file's directory, not project_root.
        # This ensures nested configs (e.g., src/mycli/cli/usecli.config.toml)
        # resolve paths correctly relative to their location.
        config_dir = self.usecli_config_path.parent
        return (config_dir / commands_path).resolve()

    def get_project_templates_dir(self) -> Path:
        templates_dir = self.get("templates_dir", "cli/templates")
        templates_path = Path(templates_dir)
        if templates_path.is_absolute():
            return templates_path
        config_dir = self.usecli_config_path.parent
        return (config_dir / templates_path).resolve()

    def get_project_themes_dirs(self) -> list[Path]:
        themes_dir = self.get("themes_dir", [])
        themes_entries = _normalize_themes_dir(themes_dir)
        result: list[Path] = []
        config_dir = self.usecli_config_path.parent
        for entry in themes_entries:
            theme_path = Path(entry)
            if not theme_path.is_absolute():
                theme_path = config_dir / theme_path
            result.append(theme_path.resolve())
        return result

    def get_project_paths(self) -> dict[str, Path]:
        project_config = self._find_project_config()
        if project_config is None:
            return {
                "commands_dir": self.get_project_commands_dir(),
                "templates_dir": self.get_project_templates_dir(),
            }
        config_dir = project_config.parent
        config_data = self._load_usecli_toml(project_config)
        commands_dir = config_data.get("commands_dir", "cli/commands")
        templates_dir = config_data.get("templates_dir", "cli/templates")
        commands_path = Path(commands_dir)
        templates_path = Path(templates_dir)
        if not commands_path.is_absolute():
            commands_path = config_dir / commands_path
        if not templates_path.is_absolute():
            templates_path = config_dir / templates_path
        return {
            "commands_dir": commands_path.resolve(),
            "templates_dir": templates_path.resolve(),
        }

    def _find_project_config(self) -> Path | None:
        start_dir = self.start_dir
        project_root = find_project_root(start_dir)
        if project_root is None:
            return None
        candidates = _rglob_limited(project_root, USECLI_CONFIG_TOML)
        if not candidates:
            return None
        candidates.sort(key=lambda p: (len(p.parts), str(p)))
        return candidates[0]

    def is_dev(self) -> bool:
        """Check if running in development environment."""
        return self.get("environment", "prod") == "dev"

    def is_prod(self) -> bool:
        """Check if running in production environment."""
        return self.get("environment", "prod") == "prod"

    def is_usecli_direct_dependency(self) -> bool:
        """Check if usecli is a direct dependency of the current project.

        Returns True when:
        - The current project IS usecli (name matches)
        - usecli appears in pyproject.toml [project.dependencies]
        - usecli appears in pyproject.toml [dependency-groups]
        """
        if not self.pyproject_path.exists():
            return False

        try:
            with open(self.pyproject_path, "rb") as f:
                data = tomllib.load(f)
        except (tomllib.TOMLDecodeError, OSError):
            return False

        project_name = data.get("project", {}).get("name", "")
        if isinstance(project_name, str) and project_name.strip().lower() == "usecli":
            return True

        for dep in data.get("project", {}).get("dependencies", []):
            if isinstance(dep, str) and dep.strip().lower().startswith("usecli"):
                return True

        for group_deps in data.get("dependency-groups", {}).values():
            if not isinstance(group_deps, list):
                continue
            for dep in group_deps:
                dep_str = dep if isinstance(dep, str) else dep.get("dependency", "")
                if isinstance(dep_str, str) and dep_str.strip().lower().startswith(
                    "usecli"
                ):
                    return True

        return False

    def reload(self) -> None:
        """Reload configuration from disk."""
        self.usecli_config_path = self._find_usecli_config(self.start_dir) or (
            self.start_dir / USECLI_CONFIG_TOML
        )
        self._load_config()

    @property
    def pyproject_exists(self) -> bool:
        return self.usecli_config_path.exists()

    @staticmethod
    def _load_project_version(path: Path) -> str | None:
        if not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except (tomllib.TOMLDecodeError, OSError):
            return None

        project_version = data.get("project", {}).get("version")
        if isinstance(project_version, str) and project_version.strip():
            return project_version.strip()

        tool_version = data.get("tool", {}).get("usecli", {}).get("version")
        if isinstance(tool_version, str) and tool_version.strip():
            return tool_version.strip()

        return None


_config_manager: ConfigManager | None = None
_config_cwd: Path | None = None


def get_config() -> ConfigManager:
    """Get the global ConfigManager instance."""
    global _config_manager, _config_cwd
    cwd = Path.cwd().resolve()
    if _config_manager is not None and _config_cwd == cwd:
        return _config_manager
    _config_manager = ConfigManager(start_dir=Path.cwd())
    _config_cwd = cwd
    return _config_manager


def reset_config() -> None:
    """Reset the global ConfigManager instance."""
    global _config_manager, _config_cwd
    _config_manager = None
    _config_cwd = None


def find_project_root(start_dir: Path | None = None) -> Path | None:
    if start_dir is None:
        start_dir = Path.cwd()

    current = start_dir.resolve()

    git_root: Path | None = None
    while True:
        pyproject_path = current / PYPROJECT_TOML
        if pyproject_path.exists():
            return current

        usecli_path = current / USECLI_CONFIG_TOML
        if usecli_path.exists():
            return current

        git_dir = current / ".git"
        if git_dir.exists():
            git_root = current
            break

        parent = current.parent
        if parent == current:
            break
        current = parent

    search_root = git_root or start_dir.resolve()

    # Skip expensive recursive search when search root is a high-level directory.
    # Global tools running from HOME or / will never find a project config this way.
    if str(search_root) in HIGH_LEVEL_DIRS:
        return git_root

    # Try fast lookups before expensive rglob (perf: global tools).
    console_match = ConfigManager._find_usecli_config_for_console_script()
    if console_match:
        return console_match.parent

    if ConfigManager._is_within_usecli_package(start_dir):
        package_match = ConfigManager._find_usecli_config_in_package()
        if package_match:
            return package_match.parent

    config_match = ConfigManager._find_usecli_config_in_tree(
        search_root,
        start_dir,
        skip_venv=True,
    )
    if config_match:
        return config_match.parent

    return git_root


def _get_package_name() -> str:
    package = __package__ or __name__
    if not package:
        return "usecli"
    return package.split(".")[0]
