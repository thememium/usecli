"""Framework-wide option hiding for the active CLI."""

from __future__ import annotations

from typing import Any

from typer.core import TyperCommand, TyperGroup

# Options usecli injects into every command and command group. Hiding one of
# these applies across all commands, not just the root help.
UNIVERSAL_OPTION_NAMES = frozenset({"interactive", "json"})


def hidden_option_names() -> set[str]:
    """Return the hidden option names for the running CLI.

    Project configs never affect the ``usecli`` framework binary.
    """
    from usecli.cli.core.ui.title import running_framework_distribution
    from usecli.shared.config.manager import get_config

    if running_framework_distribution() is not None:
        return set()
    return set(get_config().get_hidden_options())


def option_names(param: Any) -> set[str]:
    """Return a parameter's long option names without leading dashes."""
    return {
        opt.lstrip("-").lower()
        for opt in getattr(param, "opts", ()) or ()
        if opt.startswith("--")
    }


def is_hidden_option(param: Any, hidden: set[str]) -> bool:
    """Whether *param* matches a hidden option name.

    ``--help``/``-h`` is never hidden.
    """
    if not hidden:
        return False
    if "--help" in (getattr(param, "opts", ()) or ()):
        return False
    return bool(option_names(param) & hidden)


def filter_hidden_params(command: Any, hidden: set[str]) -> None:
    """Remove params matching *hidden* from *command* in place."""
    if not hidden:
        return
    params = getattr(command, "params", None)
    if not params:
        return
    command.params = [param for param in params if not is_hidden_option(param, hidden)]


def filter_universal_hidden_params(command: Any) -> None:
    """Remove universally hidden options (``--interactive``/``--json``)."""
    filter_hidden_params(command, hidden_option_names() & UNIVERSAL_OPTION_NAMES)


class HiddenOptionsCommand(TyperCommand):
    """Command that drops universally hidden options before parsing."""

    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: Any | None = None,
        **extra: Any,
    ) -> Any:
        filter_universal_hidden_params(self)
        return super().make_context(info_name, args, parent=parent, **extra)


class HiddenOptionsGroup(TyperGroup):
    """Group that drops universally hidden options before parsing."""

    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: Any | None = None,
        **extra: Any,
    ) -> Any:
        filter_universal_hidden_params(self)
        return super().make_context(info_name, args, parent=parent, **extra)
