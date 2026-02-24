"""Global color constants for usecli CLI.

Usage:
    from usecli.cli.config.colors import COLOR

    console.print(f"[{COLOR.PRIMARY}]Hello[/]")
    console.print(f"[{COLOR.ERROR}]Failed[/]")
    console.print(f"[{COLOR.STYLE.HEADER}]Section[/]")
    print(f"{COLOR.ANSI.SECONDARY}styled text{COLOR.ANSI.RESET}")
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any, Callable, Final, final

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


PYPROJECT_TOML = "pyproject.toml"
USECLI_CONFIG_TOML = "usecli.config.toml"
DEFAULT_THEME_NAME = "default"
THEMES_DIR = Path(__file__).resolve().parent.parent / "themes"
_SKIP_DIRS = {
    ".venv",
    "venv",
    "site-packages",
    "dist-packages",
    "__pypackages__",
    "pipx",
    "venvs",
}
DEFAULT_THEME_COLORS: dict[str, str] = {
    "primary": "#60D7FF",
    "secondary": "#5EFF87",
    "accent": "#F5FE53",
    "success": "#5EFF87",
    "error": "#FE686B",
    "warning": "#F5FE53",
    "info": "#60D7FF",
    "foreground": "#FFFFFF",
    "foreground_muted": "#BBBBBB",
    "background": "#000000",
    "border": "#60D7FF",
    "border_focus": "#5EFF87",
    "command": "#60D7FF",
    "option": "#60D7FF",
    "link": "#60D7FF",
    "prompt": "#5EFF87",
    "panel_primary": "#5EFF87",
    "panel_secondary": "#60D7FF",
    "panel_accent": "#F5FE53",
}


def _find_usecli_config_path(
    root_dir: Path, start_dir: Path, *, skip_venv: bool
) -> Path | None:
    if not root_dir.exists() or not root_dir.is_dir():
        return None

    candidates = [path for path in root_dir.rglob(USECLI_CONFIG_TOML)]
    if skip_venv:
        candidates = [
            path
            for path in candidates
            if not any(part in _SKIP_DIRS for part in path.parts)
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


def _find_usecli_config_in_package() -> Path | None:
    spec = importlib.util.find_spec(_get_package_name())
    if spec is None or not spec.submodule_search_locations:
        return None
    for location in spec.submodule_search_locations:
        package_root = Path(location)
        if not package_root.exists() or not package_root.is_dir():
            continue
        candidates = [
            path for path in package_root.rglob(USECLI_CONFIG_TOML) if path.exists()
        ]
        if candidates:
            candidates.sort(key=lambda path: (len(path.parts), str(path)))
            return candidates[0]
    return None


def _find_usecli_config_in_named_package(package_name: str) -> Path | None:
    if not package_name:
        return None
    spec = importlib.util.find_spec(package_name)
    if spec is None or not spec.submodule_search_locations:
        return None
    for location in spec.submodule_search_locations:
        package_root = Path(location)
        if not package_root.exists() or not package_root.is_dir():
            continue
        candidates = [
            path for path in package_root.rglob(USECLI_CONFIG_TOML) if path.exists()
        ]
        if candidates:
            candidates.sort(key=lambda path: (len(path.parts), str(path)))
            return candidates[0]
    return None


def _find_usecli_config_for_console_script() -> Path | None:
    command_name = os.path.basename(sys.argv[0]) if sys.argv else ""
    if not command_name:
        return None
    try:
        distributions = importlib.metadata.distributions()
    except Exception:
        return None
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
            candidates: list[str] = []
            if dist_name:
                candidates.append(dist_name)
                normalized = dist_name.replace("-", "_")
                if normalized not in candidates:
                    candidates.append(normalized)
            for package_name in candidates:
                match = _find_usecli_config_in_named_package(package_name)
                if match:
                    return match
    return None


def _is_preferred_package_path(path: Path) -> bool:
    return any(part in _SKIP_DIRS for part in path.parts)


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


def _find_project_root(start_dir: Path | None = None) -> Path | None:
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
    config_match = _find_usecli_config_path(search_root, start_dir, skip_venv=True)
    if config_match:
        return config_match.parent

    console_match = _find_usecli_config_for_console_script()
    if console_match:
        return console_match.parent

    package_match = _find_usecli_config_in_package()
    if package_match:
        return package_match.parent

    return git_root


def _load_usecli_config(project_root: Path | None) -> dict[str, Any]:
    if project_root is None:
        return {}

    config_path = project_root / USECLI_CONFIG_TOML
    if not config_path.exists():
        config_path = _find_usecli_config_path(
            project_root,
            project_root,
            skip_venv=True,
        )
    if not config_path or not config_path.exists():
        console_match = _find_usecli_config_for_console_script()
        if console_match:
            return _load_usecli_config_file(console_match)
        package_match = _find_usecli_config_in_package()
        if package_match:
            config_path = package_match
    if not config_path or not config_path.exists():
        return {}

    return _load_usecli_config_file(config_path)


def _load_usecli_config_file(config_path: Path) -> dict[str, Any]:
    try:
        data = tomllib.loads(config_path.read_text())
    except (tomllib.TOMLDecodeError, OSError):
        return {}

    tool = data.get("tool", {})
    if isinstance(tool, dict) and "usecli" in tool:
        usecli_config = tool.get("usecli")
        if isinstance(usecli_config, dict):
            return usecli_config

    usecli_section = data.get("usecli", {})
    if isinstance(usecli_section, dict):
        return usecli_section

    return {}


def _get_package_name() -> str:
    package = __package__ or __name__
    if not package:
        return "usecli"
    return package.split(".")[0]


def _normalize_color(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    return value


def _hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    if value.startswith("#"):
        value = value[1:]
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        return None
    try:
        r = int(value[0:2], 16)
        g = int(value[2:4], 16)
        b = int(value[4:6], 16)
    except ValueError:
        return None
    return r, g, b


def _ansi_from_hex(value: str) -> str | None:
    rgb = _hex_to_rgb(value)
    if rgb is None:
        return None
    r, g, b = rgb
    return f"\033[38;2;{r};{g};{b}m"


def _merge_theme_values(
    defaults: dict[str, str],
    overrides: dict[str, Any],
    normalize: Callable[[Any], str | None],
) -> dict[str, str]:
    result = defaults.copy()
    if not isinstance(overrides, dict):
        return result

    for key, value in overrides.items():
        if key not in result:
            continue
        normalized = normalize(value)
        if normalized:
            result[key] = normalized
    return result


def _normalize_theme_dirs(value: Any, project_root: Path | None) -> list[Path]:
    if value is None:
        return []
    entries: list[str] = []
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            entries.append(normalized)
    elif isinstance(value, list):
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip()
            if normalized:
                entries.append(normalized)

    result: list[Path] = []
    for entry in entries:
        path = Path(entry)
        if not path.is_absolute():
            if project_root is None:
                continue
            path = project_root / path
        result.append(path)
    return result


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append(path)
    return result


def _get_theme_dirs(project_root: Path | None, config: dict[str, Any]) -> list[Path]:
    default_dirs: list[Path] = []
    if project_root is not None:
        default_dirs.append(project_root / "cli" / "themes")

    config_dirs = _normalize_theme_dirs(config.get("themes_dir"), project_root)
    merged = _dedupe_paths(default_dirs + config_dirs)
    return _dedupe_paths(merged + [THEMES_DIR])


def _build_ansi_palette(colors: dict[str, str]) -> dict[str, str]:
    def pick(key: str) -> str:
        value = colors.get(key, DEFAULT_THEME_COLORS[key])
        ansi = _ansi_from_hex(value)
        if ansi is None:
            ansi = _ansi_from_hex(DEFAULT_THEME_COLORS[key])
        return ansi or ""

    ansi: dict[str, str] = {
        "reset": "\033[0m",
    }

    primary = pick("primary")
    secondary = pick("secondary")
    accent = pick("accent")
    foreground = pick("foreground")
    foreground_muted = pick("foreground_muted")
    error = pick("error")
    success = pick("success")
    warning = pick("warning")

    ansi["primary"] = primary
    ansi["blue"] = primary
    ansi["secondary"] = secondary
    ansi["accent"] = accent
    ansi["foreground"] = foreground
    ansi["foreground_muted"] = foreground_muted
    ansi["red"] = error
    ansi["green"] = success
    ansi["yellow"] = warning

    return ansi


def _resolve_theme_path(
    theme_name: str, project_root: Path | None, config: dict[str, Any]
) -> Path | None:
    if not theme_name:
        return None

    normalized = theme_name.strip()
    if not normalized:
        return None

    if normalized.endswith(".toml") or "/" in normalized or "\\" in normalized:
        theme_path = Path(normalized)
        if not theme_path.is_absolute() and project_root is not None:
            theme_path = project_root / theme_path
        if theme_path.exists():
            return theme_path
        return None

    for theme_dir in _get_theme_dirs(project_root, config):
        theme_path = theme_dir / f"{normalized}.toml"
        if theme_path.exists():
            return theme_path

    return None


def _load_theme_file(theme_path: Path) -> dict[str, Any]:
    try:
        with open(theme_path, "rb") as theme_file:
            data = tomllib.load(theme_file)
    except (tomllib.TOMLDecodeError, OSError):
        return {}

    if not isinstance(data, dict):
        return {}

    return data


def _load_theme() -> tuple[dict[str, str], dict[str, str]]:
    project_root = _find_project_root()
    config = _load_usecli_config(project_root)

    theme_name = DEFAULT_THEME_NAME
    config_theme = config.get("theme")
    if isinstance(config_theme, str) and config_theme.strip():
        theme_name = config_theme.strip()

    theme_path = _resolve_theme_path(theme_name, project_root, config)
    theme_data = _load_theme_file(theme_path) if theme_path else {}

    colors = _merge_theme_values(
        DEFAULT_THEME_COLORS,
        theme_data.get("colors", {}),
        _normalize_color,
    )
    ansi = _build_ansi_palette(colors)

    return colors, ansi


_THEME_COLORS, _THEME_ANSI = _load_theme()


@final
class COLOR:
    """Semantic color system for usecli CLI.

    All colors are defined as hex color codes compatible with Rich console.
    ANSI codes are available via COLOR.ANSI.* for non-Rich outputs.
    Style presets are available via COLOR.STYLE.* for common patterns.

    Examples:
        >>> console.print(f"[{COLOR.PRIMARY}]Hello World[/]")
        >>> console.print(f"[{COLOR.STYLE.HEADER}]Section[/]")
        >>> print(f"{COLOR.ANSI.SECONDARY}text{COLOR.ANSI.RESET}")
        >>> panel = Panel("Content", border_style=COLOR.SECONDARY)
    """

    # ==========================================================================
    # Hex Color Codes (for Rich console)
    # ==========================================================================

    # Brand colors
    PRIMARY: Final[str] = _THEME_COLORS["primary"]
    SECONDARY: Final[str] = _THEME_COLORS["secondary"]
    ACCENT: Final[str] = _THEME_COLORS["accent"]

    # Functional colors
    SUCCESS: Final[str] = _THEME_COLORS["success"]
    ERROR: Final[str] = _THEME_COLORS["error"]
    WARNING: Final[str] = _THEME_COLORS["warning"]
    INFO: Final[str] = _THEME_COLORS["info"]

    # UI colors
    FOREGROUND: Final[str] = _THEME_COLORS["foreground"]
    FOREGROUND_MUTED: Final[str] = _THEME_COLORS["foreground_muted"]
    BACKGROUND: Final[str] = _THEME_COLORS["background"]
    BORDER: Final[str] = _THEME_COLORS["border"]
    BORDER_FOCUS: Final[str] = _THEME_COLORS["border_focus"]

    # Interactive elements
    COMMAND: Final[str] = _THEME_COLORS["command"]
    OPTION: Final[str] = _THEME_COLORS["option"]
    LINK: Final[str] = _THEME_COLORS["link"]
    PROMPT: Final[str] = _THEME_COLORS["prompt"]

    # Panel colors
    PANEL_PRIMARY: Final[str] = _THEME_COLORS["panel_primary"]
    PANEL_SECONDARY: Final[str] = _THEME_COLORS["panel_secondary"]
    PANEL_ACCENT: Final[str] = _THEME_COLORS["panel_accent"]

    # ==========================================================================
    # Nested: ANSI Escape Sequences (for non-Rich outputs like fzf)
    # ==========================================================================

    @final
    class ANSI:
        """ANSI escape sequences for terminal styling.

        Use these when you need to output styled text directly to the terminal
        without using Rich console (e.g., for fzf integration).

        Examples:
            >>> print(f"{COLOR.ANSI.SECONDARY}text{COLOR.ANSI.RESET}")
        """

        # Palette colors as ANSI
        PRIMARY: Final[str] = _THEME_ANSI["primary"]
        SECONDARY: Final[str] = _THEME_ANSI["secondary"]
        ACCENT: Final[str] = _THEME_ANSI["accent"]
        FOREGROUND: Final[str] = _THEME_ANSI["foreground"]
        FOREGROUND_MUTED: Final[str] = _THEME_ANSI["foreground_muted"]

        # Standard ANSI colors
        RESET: Final[str] = _THEME_ANSI["reset"]
        RED: Final[str] = _THEME_ANSI["red"]
        GREEN: Final[str] = _THEME_ANSI["green"]
        YELLOW: Final[str] = _THEME_ANSI["yellow"]
        BLUE: Final[str] = _THEME_ANSI["blue"]


def bold(color: str) -> str:
    """Wrap color in bold tag for Rich.

    Usage:
        console.print(f"[{bold(COLOR.PRIMARY)}]Important![/]")
    """
    return f"bold {color}"


def style(text: str, color: str, *, bold: bool = False) -> str:
    """Apply color style to text for Rich console.

    Usage:
        console.print(style("Success!", COLOR.SUCCESS))
        console.print(style("Error", COLOR.ERROR, bold=True))
    """
    if bold:
        return f"[bold {color}]{text}[/bold {color}]"
    return f"[{color}]{text}[/{color}]"
