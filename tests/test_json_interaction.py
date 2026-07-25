"""Tests for non-interactive UI behavior in JSON mode."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from usecli import Confirm, Menu, Prompt
from usecli.cli.core import runtime
from usecli.cli.utils.interactive.terminal_menu import terminal_menu


def _non_interactive_error() -> type[Exception]:
    error_type = getattr(runtime, "NonInteractiveError", None)
    assert error_type is not None, "NonInteractiveError is not implemented"
    return error_type


def test_prompt_returns_declared_default_without_reading_input() -> None:
    with (
        runtime.execution_context(json_mode=True),
        patch("usecli.ui.RichPrompt.ask") as rich_ask,
    ):
        result = Prompt.ask("Name", default="automation")

    assert result == "automation"
    rich_ask.assert_not_called()


def test_confirm_returns_false_default_without_reading_input() -> None:
    with (
        runtime.execution_context(json_mode=True),
        patch("usecli.ui.RichConfirm.ask") as rich_ask,
    ):
        result = Confirm.ask("Continue?", default=False)

    assert result is False
    rich_ask.assert_not_called()


def test_prompt_without_default_fails_before_reading_input() -> None:
    with (
        runtime.execution_context(json_mode=True),
        patch("usecli.ui.RichPrompt.ask") as rich_ask,
        pytest.raises(_non_interactive_error(), match="Prompt.*default"),
    ):
        Prompt.ask("Name")

    rich_ask.assert_not_called()


@pytest.mark.parametrize("method_name", ["select", "multi_select"])
def test_menu_fails_before_opening_terminal(method_name: str) -> None:
    method = getattr(Menu, method_name)

    with (
        runtime.execution_context(json_mode=True),
        patch("usecli.menu.terminal_menu") as menu_impl,
        pytest.raises(_non_interactive_error(), match="menu"),
    ):
        method(["one", "two"])

    menu_impl.assert_not_called()


def test_terminal_menu_guard_cannot_be_bypassed() -> None:
    with (
        runtime.execution_context(json_mode=True),
        patch(
            "usecli.cli.utils.interactive.terminal_menu.TerminalMenu"
        ) as terminal_menu_type,
        pytest.raises(_non_interactive_error(), match="menu"),
    ):
        terminal_menu(["one", "two"])

    terminal_menu_type.assert_not_called()
