"""Parameter definitions for usecli - wrappers around Typer parameters."""

from __future__ import annotations

from typing import Any

import typer


def Argument(
    default: Any = ...,
    *,
    help: str | None = None,
    show_default: bool = True,
    show_choices: bool = True,
    **kwargs: Any,
) -> Any:
    """Create a command-line argument.

    This is a wrapper around typer.Argument that provides sensible defaults
    for usecli commands.

    Args:
        default: The default value for the argument. Use ... for required arguments.
        help: Help text displayed in command help.
        show_default: Whether to show the default value in help text.
        show_choices: Whether to show valid choices in help text.
        **kwargs: Additional arguments passed to typer.Argument.

    Returns:
        A Typer Argument parameter.

    Example:
        >>> def handle(self, name: str = Argument(..., help="Your name")):
        ...     console.print(f"Hello, {name}!")
    """
    return typer.Argument(
        default=default,
        help=help,
        show_default=show_default,
        show_choices=show_choices,
        **kwargs,
    )


def Option(
    default: Any = None,
    *param_decls: str,
    help: str | None = None,
    show_default: bool = True,
    show_choices: bool = True,
    is_flag: bool = False,
    **kwargs: Any,
) -> Any:
    """Create a command-line option.

    This is a wrapper around typer.Option that provides sensible defaults
    for usecli commands.

    Args:
        default: The default value for the option.
        *param_decls: Option names (e.g., "--verbose", "-v").
        help: Help text displayed in command help.
        show_default: Whether to show the default value in help text.
        show_choices: Whether to show valid choices in help text.
        is_flag: Whether this option is a boolean flag.
        **kwargs: Additional arguments passed to typer.Option.

    Returns:
        A Typer Option parameter.

    Example:
        >>> def handle(
        ...     self,
        ...     verbose: bool = Option(False, "--verbose", "-v", help="Enable verbose output")
        ... ):
        ...     if verbose:
        ...         console.print("Verbose mode enabled")
    """
    if is_flag and default is None:
        default = False

    return typer.Option(
        default,
        *param_decls,
        help=help,
        show_default=show_default,
        show_choices=show_choices,
        **kwargs,
    )


__all__ = ["Argument", "Option"]
