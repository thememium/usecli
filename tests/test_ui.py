"""Tests for usecli.ui, focused on single-key confirmation."""

from __future__ import annotations

import sys
import types
from typing import Any, cast
from unittest.mock import PropertyMock, patch

import pytest

from usecli import Confirm
from usecli.ui import _ask_single_key, _can_read_single_key, _read_key, console


class _FakeStdin:
    encoding = "utf-8"

    def __init__(self, *, tty: bool = True) -> None:
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty

    def fileno(self) -> int:
        return 7


@pytest.mark.parametrize(
    ("key", "expected"),
    [("y", True), ("Y", True), ("n", False), ("N", False)],
)
def test_confirm_returns_on_first_keypress(key: str, expected: bool) -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", return_value=key),
        patch("usecli.ui.RichConfirm.ask") as rich_ask,
    ):
        assert Confirm.ask("Continue?", single_key=True) is expected

    rich_ask.assert_not_called()


def test_confirm_enter_accepts_default() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", return_value="\r"),
    ):
        assert Confirm.ask("Continue?", default=False, single_key=True) is False


def test_confirm_ctrl_d_accepts_default() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", return_value="\x04"),
    ):
        assert Confirm.ask("Continue?", default=True, single_key=True) is True


def test_confirm_ctrl_c_interrupts() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", return_value="\x03"),
        pytest.raises(KeyboardInterrupt),
    ):
        Confirm.ask("Continue?", single_key=True)


def test_confirm_ignores_unrelated_keys() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", side_effect=["x", "\x1b", "[", "A", "n"]),
    ):
        assert Confirm.ask("Continue?", single_key=True) is False


def test_confirm_renders_rich_prompt_with_choices() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", return_value="y"),
        patch.object(console, "print") as console_print,
    ):
        _ask_single_key("Continue?", default=True)

    rendered = str(console_print.call_args_list[0].args[0])
    assert rendered == "Continue? [y/n] (y): "


def test_confirm_falls_back_to_rich_without_tty() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=False),
        patch("usecli.ui.RichConfirm.ask", return_value=True) as rich_ask,
    ):
        assert Confirm.ask("Continue?", single_key=True) is True

    rich_ask.assert_called_once()


def test_confirm_regular_mode_delegates_even_in_terminal() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._ask_single_key") as single_key,
        patch("usecli.ui.RichConfirm.ask", return_value=False) as rich_ask,
    ):
        assert Confirm.ask("Continue?") is False

    rich_ask.assert_called_once()
    single_key.assert_not_called()


def test_can_read_single_key_requires_tty_stdin_and_stdout() -> None:
    with (
        patch("usecli.ui.sys.stdin", _FakeStdin(tty=True)),
        patch.object(
            type(console),
            "is_terminal",
            new_callable=PropertyMock,
            return_value=True,
        ),
    ):
        assert _can_read_single_key() is True

    with patch("usecli.ui.sys.stdin", _FakeStdin(tty=False)):
        assert _can_read_single_key() is False


def test_can_read_single_key_without_isatty() -> None:
    with patch("usecli.ui.sys.stdin", object()):
        assert _can_read_single_key() is False


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX terminal API")
def test_read_key_restores_terminal_mode() -> None:
    import termios

    with (
        patch("usecli.ui.sys.stdin", _FakeStdin()),
        patch("termios.tcgetattr", return_value=["attrs"]),
        patch("termios.tcsetattr") as tcsetattr,
        patch("tty.setcbreak") as setcbreak,
        patch("os.read", return_value=b"y") as read,
    ):
        assert _read_key() == "y"

    setcbreak.assert_called_once_with(7, termios.TCSADRAIN)
    read.assert_called_once_with(7, 1)
    tcsetattr.assert_called_once_with(7, termios.TCSADRAIN, ["attrs"])


def test_read_key_uses_msvcrt_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_msvcrt = cast(Any, types.ModuleType("msvcrt"))
    fake_msvcrt.getwch = lambda: "n"
    monkeypatch.setitem(sys.modules, "msvcrt", fake_msvcrt)
    monkeypatch.setattr(sys, "platform", "win32")

    assert _read_key() == "n"
