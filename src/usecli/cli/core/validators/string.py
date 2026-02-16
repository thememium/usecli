"""Parameter validation callbacks for strings.

These validators integrate with UsecliBadParameter for consistent
error styling across the CLI.
"""

from __future__ import annotations

import re

from usecli.cli.core.exceptions import UsecliBadParameter


def validate_not_empty(value: str) -> str:
    """Validate that a string value is not empty.

    Args:
        value: The string value to validate.

    Returns:
        The validated value.

    Raises:
        UsecliBadParameter: If the value is empty or whitespace only.
    """
    if not value or not value.strip():
        raise UsecliBadParameter("Value cannot be empty", param_hint="value")
    return value


def validate_command_name(value: str) -> str:
    """Validate command name format.

    Command names must:
    - Not be empty
    - Contain only alphanumeric characters, underscores, and hyphens
    - Not start with a number

    Args:
        value: The command name to validate.

    Returns:
        The validated command name.

    Raises:
        UsecliBadParameter: If the command name is invalid.
    """
    if not value:
        raise UsecliBadParameter("Command name cannot be empty", param_hint="NAME")

    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", value):
        raise UsecliBadParameter(f"Invalid command name: '{value}'", param_hint="NAME")

    return value
