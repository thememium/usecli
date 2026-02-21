"""Global color constants for usecli CLI.

Usage:
    from usecli.cli.config.colors import COLOR

    console.print(f"[{COLOR.PRIMARY}]Hello[/]")
    console.print(f"[{COLOR.ERROR}]Failed[/]")
    console.print(f"[{COLOR.STYLE.HEADER}]Section[/]")
    print(f"{COLOR.ANSI.SECONDARY}styled text{COLOR.ANSI.RESET}")
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Final, final

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


DEFAULT_THEME_NAME = "default"
THEMES_DIR = Path(__file__).resolve().parent.parent / "themes"
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
DEFAULT_THEME_ANSI: dict[str, str] = {
    "primary": "\033[38;2;96;215;255m",
    "secondary": "\033[38;2;94;255;135m",
    "accent": "\033[38;2;216;176;0m",
    "foreground": "\033[38;2;255;255;255m",
    "foreground_muted": "\033[38;2;158;158;158m",
    "reset": "\033[0m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
}


def _find_project_root(start_dir: Path | None = None) -> Path | None:
    if start_dir is None:
        start_dir = Path.cwd()

    current = start_dir.resolve()

    while True:
        pyproject_path = current / "pyproject.toml"
        if pyproject_path.exists():
            return current

        git_dir = current / ".git"
        if git_dir.exists():
            return current

        parent = current.parent
        if parent == current:
            break
        current = parent

    return None


def _load_usecli_config(project_root: Path | None) -> dict[str, Any]:
    if project_root is None:
        return {}

    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        return {}

    try:
        data = tomllib.loads(pyproject_path.read_text())
    except (tomllib.TOMLDecodeError, OSError):
        return {}

    tool = data.get("tool", {})
    if not isinstance(tool, dict):
        return {}

    usecli_config = tool.get("usecli", {})
    if not isinstance(usecli_config, dict):
        return {}

    return usecli_config


def _normalize_color(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None
    return value


def _normalize_ansi(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value:
        return None

    if value.startswith("\033[") or value.startswith("\x1b["):
        return value if value.endswith("m") else f"{value}m"

    if value.startswith("["):
        value = value[1:]
    if value.endswith("m"):
        value = value[:-1]

    return f"\033[{value}m"


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


def _resolve_theme_path(theme_name: str, project_root: Path | None) -> Path | None:
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

    if project_root is not None:
        project_theme = project_root / "cli" / "themes" / f"{normalized}.toml"
        if project_theme.exists():
            return project_theme

    package_theme = THEMES_DIR / f"{normalized}.toml"
    if package_theme.exists():
        return package_theme

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

    theme_path = _resolve_theme_path(theme_name, project_root)
    theme_data = _load_theme_file(theme_path) if theme_path else {}

    colors = _merge_theme_values(
        DEFAULT_THEME_COLORS,
        theme_data.get("colors", {}),
        _normalize_color,
    )
    ansi = _merge_theme_values(
        DEFAULT_THEME_ANSI,
        theme_data.get("ansi", {}),
        _normalize_ansi,
    )

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
