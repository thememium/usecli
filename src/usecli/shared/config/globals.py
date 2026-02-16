"""Global configuration and paths for usecli."""

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

# Project paths (for generated commands in the current working directory)
PROJECT_COMMANDS_DIR = Path.cwd() / "cli" / "commands"

# Global config paths
GLOBAL_CONFIG_DIR = Path.home() / ".config" / "usecli"
GLOBAL_CONFIG_PATH = GLOBAL_CONFIG_DIR / "config.yaml"
