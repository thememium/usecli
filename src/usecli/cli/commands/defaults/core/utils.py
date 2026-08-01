"""Shared utilities for useCli commands."""

from __future__ import annotations

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path


class _LazyConsole:
    _console = None

    def _get_console(self):
        if self._console is None:
            from rich.console import Console

            self._console = Console()
        return self._console

    def __getattr__(self, name):
        return getattr(self._get_console(), name)


console = _LazyConsole()


def is_interactive() -> bool:
    """Check if the current terminal is interactive.

    Returns:
        True if stdin is a tty, False otherwise.
    """
    return sys.stdin.isatty()


def get_active_change_ids(project_path: Path | None = None) -> list[str]:
    """Get list of active (non-archived) change IDs.

    Args:
        project_path: Path to the project root. Defaults to current directory.

    Returns:
        List of change directory names.
    """
    if project_path is None:
        project_path = Path.cwd()

    changes_dir = project_path / "usecli" / "changes"
    if not changes_dir.exists():
        return []

    changes = []
    for item in changes_dir.iterdir():
        if item.is_dir() and item.name != "archive":
            changes.append(item.name)

    return sorted(changes)


def get_spec_ids(project_path: Path | None = None) -> list[str]:
    """Get list of spec IDs from the specs directory.

    Args:
        project_path: Path to the project root. Defaults to current directory.

    Returns:
        List of spec directory names.
    """
    if project_path is None:
        project_path = Path.cwd()

    specs_dir = project_path / "usecli" / "specs"
    if not specs_dir.exists():
        return []

    specs = []
    for item in specs_dir.iterdir():
        if item.is_dir():
            specs.append(item.name)

    return sorted(specs)


def validate_change_name(name: str) -> tuple[bool, str]:
    """Validate a change name according to useCli conventions.

    Args:
        name: The change name to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not name:
        return False, "Change name cannot be empty"

    if not re.match(r"^[a-z0-9-]+$", name):
        return (
            False,
            "Change name must contain only lowercase letters, numbers, and hyphens",
        )

    if name.startswith("-") or name.endswith("-"):
        return False, "Change name cannot start or end with a hyphen"

    if "--" in name:
        return False, "Change name cannot contain consecutive hyphens"

    return True, ""


def format_relative_time(timestamp: datetime) -> str:
    """Format a datetime as a relative time string.

    Args:
        timestamp: The datetime to format.

    Returns:
        Relative time string (e.g., "2 hours ago", "3 days ago").
    """
    now = datetime.now()
    diff = now - timestamp

    if diff < timedelta(minutes=1):
        return "just now"
    if diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if diff < timedelta(days=30):
        days = diff.days
        return f"{days} day{'s' if days != 1 else ''} ago"
    if diff < timedelta(days=365):
        months = int(diff.days / 30)
        return f"{months} month{'s' if months != 1 else ''} ago"

    years = int(diff.days / 365)
    return f"{years} year{'s' if years != 1 else ''} ago"


def find_usecli_root(start_path: Path | None = None) -> Path | None:
    """Find the useCli project root by looking for usecli directory.

    Args:
        start_path: Path to start searching from. Defaults to current directory.

    Returns:
        Path to the project root, or None if not found.
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    while current != current.parent:
        usecli_dir = current / "usecli"
        if usecli_dir.exists() and usecli_dir.is_dir():
            return current
        current = current.parent

    return None


def get_change_path(change_id: str, project_path: Path | None = None) -> Path | None:
    """Get the path to a change directory.

    Args:
        change_id: The ID of the change.
        project_path: Path to the project root. Defaults to current directory.

    Returns:
        Path to the change directory, or None if not found.
    """
    if project_path is None:
        project_path = Path.cwd()

    change_path = project_path / "usecli" / "changes" / change_id
    if change_path.exists():
        return change_path

    return None


def get_spec_path(spec_id: str, project_path: Path | None = None) -> Path | None:
    """Get the path to a spec directory.

    Args:
        spec_id: The ID of the spec.
        project_path: Path to the project root. Defaults to current directory.

    Returns:
        Path to the spec directory, or None if not found.
    """
    if project_path is None:
        project_path = Path.cwd()

    spec_path = project_path / "usecli" / "specs" / spec_id
    if spec_path.exists():
        return spec_path

    return None
