"""Compatibility helpers for typer's private parameter API.

Typer >= 0.28 replaced ``TyperOption``'s ``type`` argument with a required
``type_descriptor``. usecli builds options directly to inject framework-wide
flags, so it must support both layouts.
"""

from __future__ import annotations

import inspect
from typing import Any

from typer.core import TyperArgument, TyperOption

_HAS_TYPE_DESCRIPTOR = (
    "type_descriptor" in inspect.signature(TyperOption.__init__).parameters
)


def _type_descriptor(annotation: type, *, argument: bool = False) -> Any:
    from typer._coercion import resolve_type_descriptor
    from typer.models import ArgumentInfo, OptionInfo

    info = ArgumentInfo() if argument else OptionInfo()
    return resolve_type_descriptor(annotation, info)


def make_option(
    *, param_decls: list[str], is_flag: bool = False, help: str | None = None
) -> TyperOption:
    """Build an option parameter for the installed typer version.

    Args:
        param_decls: Click-style declarations, e.g. ``["--json"]``.
        is_flag: Whether the option is a boolean flag.
        help: Help text shown in generated help output.

    Returns:
        The option parameter to append to a command's ``params``.
    """
    if not _HAS_TYPE_DESCRIPTOR:  # pragma: no cover - typer < 0.28 only
        if is_flag:
            return TyperOption(  # ty: ignore[missing-argument]
                param_decls=param_decls, is_flag=True, help=help
            )
        return TyperOption(  # ty: ignore[missing-argument]
            param_decls=param_decls, help=help
        )

    return TyperOption(
        param_decls=param_decls,
        is_flag=is_flag,
        help=help,
        type_descriptor=_type_descriptor(bool if is_flag else str),
    )


def make_argument(*, param_decls: list[str]) -> TyperArgument:
    """Build a positional argument parameter for the installed typer version."""
    if not _HAS_TYPE_DESCRIPTOR:  # pragma: no cover - typer < 0.28 only
        return TyperArgument(param_decls=param_decls)  # ty: ignore[missing-argument]

    return TyperArgument(
        param_decls=param_decls,
        type_descriptor=_type_descriptor(str, argument=True),
    )
