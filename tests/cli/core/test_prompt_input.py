"""Tests for the rich Console.input integration used by interactive prompts."""

from __future__ import annotations

import io
import sys
from types import SimpleNamespace
from typing import Any

import pytest
from rich.console import Console

from usecli.cli.utils.interactive import prompt_input


class TtyStream(io.StringIO):
    """StringIO that claims to be a terminal."""

    def isatty(self) -> bool:
        return True


def use_tty(monkeypatch: pytest.MonkeyPatch) -> TtyStream:
    """Point stdin and stdout at terminal-like streams.

    Patched inside the test body: pytest reinstalls its capture streams when
    the call phase starts, after fixtures have run.
    """
    stream = TtyStream()
    monkeypatch.setattr(sys, "stdin", TtyStream())
    monkeypatch.setattr(sys, "stdout", stream)
    return stream


def test_is_tty_requires_isatty() -> None:
    assert prompt_input._is_tty(TtyStream())
    assert not prompt_input._is_tty(io.StringIO())
    assert not prompt_input._is_tty(object())


def test_can_prompt_inline_requires_shared_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = use_tty(monkeypatch)
    assert prompt_input._can_prompt_inline(SimpleNamespace(file=stream))
    assert not prompt_input._can_prompt_inline(SimpleNamespace(file=io.StringIO()))


def test_can_prompt_inline_rejects_missing_streams(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console: Any = SimpleNamespace(file=object())
    monkeypatch.setattr(sys, "stdin", None)
    assert not prompt_input._can_prompt_inline(console)
    monkeypatch.setattr(sys, "stdin", TtyStream())
    monkeypatch.setattr(sys, "stdout", None)
    assert not prompt_input._can_prompt_inline(console)


def test_prompt_session_is_created_once(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[Any] = []

    class FakeSession:
        def __init__(self, history: Any, *, reserve_space_for_menu: int) -> None:
            created.append((history, reserve_space_for_menu))

    monkeypatch.setattr("prompt_toolkit.PromptSession", FakeSession)
    monkeypatch.setattr(prompt_input, "_session", None)

    first = prompt_input._prompt_session()
    second = prompt_input._prompt_session()

    assert first is second
    assert len(created) == 1


def test_install_is_idempotent() -> None:
    prompt_input.install_prompt_input()
    installed = Console.input
    prompt_input.install_prompt_input()
    assert Console.input is installed


def test_edit_line_prefills_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    class FakeSession:
        def prompt(self, message: Any, *, default: str = "") -> str:
            calls["message"] = message
            calls["default"] = default
            return default + "--more"

    monkeypatch.setattr(prompt_input, "_session", FakeSession())

    assert prompt_input.edit_line("usecli about ") == "usecli about --more"
    assert calls["default"] == "usecli about "


def test_inline_prompt_uses_session(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = use_tty(monkeypatch)
    messages: list[Any] = []

    class FakeSession:
        def prompt(self, message: Any) -> str:
            messages.append(message)
            return "answer"

    monkeypatch.setattr(prompt_input, "_session", FakeSession())
    prompt_input.install_prompt_input()

    console = Console(file=stream)
    assert console.input("[bold]Name[/bold]") == "answer"
    assert "Name" in messages[0].value


def test_non_terminal_prompt_uses_rich_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    def fake_input(prompt: str = "") -> str:
        seen.append(prompt)
        return "typed"

    monkeypatch.setattr("builtins.input", fake_input)
    prompt_input.install_prompt_input()

    console = Console(file=io.StringIO())
    assert console.input("Name") == "typed"
    assert seen == [""]


def test_prompt_reads_supplied_stream() -> None:
    prompt_input.install_prompt_input()

    console = Console(file=io.StringIO())
    assert console.input("Name", stream=io.StringIO("value\n")) == "value\n"
