"""Global paths for usecli."""

from __future__ import annotations

from pathlib import Path

# Package root (src/usecli/)
PACKAGE_ROOT = Path(__file__).parent.parent.parent

# CLI paths (internal package paths)
CLI_ROOT = PACKAGE_ROOT / "cli"
COMMANDS_DIR = CLI_ROOT / "commands"
CUSTOM_COMMANDS_DIR = COMMANDS_DIR / "custom"
DEFAULTS_DIR = COMMANDS_DIR / "defaults"
TEMPLATES_DIR = CLI_ROOT / "templates"
THEMES_DIR = CLI_ROOT / "themes"

# Config file names
PYPROJECT_TOML = "pyproject.toml"
