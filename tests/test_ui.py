"""Tests for usecli.ui, focused on single-key confirmation."""

from __future__ import annotations

import sys
import types
from typing import Any, cast
from unittest.mock import PropertyMock, patch

import pytest

from usecli import Confirm, Prompt
from usecli.cli.core import runtime
from usecli.cli.core.runtime import NonInteractiveError
from usecli.ui import (
    _ask_masked,
    _ask_single_key,
    _can_read_single_key,
    _read_key,
    console,
)


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


def test_prompt_passes_rich_options_through() -> None:
    with patch("usecli.ui.RichPrompt.ask", return_value="secret") as rich_ask:
        result = Prompt.ask(
            "Token",
            default="fallback",
            choices=["one", "two"],
            show_choices=False,
            show_default=False,
            password=True,
            case_sensitive=False,
        )

    assert result == "secret"
    kwargs = rich_ask.call_args.kwargs
    assert kwargs["default"] == "fallback"
    assert kwargs["choices"] == ["one", "two"]
    assert kwargs["show_choices"] is False
    assert kwargs["show_default"] is False
    assert kwargs["password"] is True
    assert kwargs["case_sensitive"] is False
    assert kwargs["console"] is console


@pytest.mark.parametrize(("key", "expected"), [("a", "a"), ("c", "c")])
def test_prompt_single_key_returns_matching_choice(key: str, expected: str) -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", return_value=key),
        patch("usecli.ui.RichPrompt.ask") as rich_ask,
    ):
        result = Prompt.ask("Mode", choices=["a", "b", "c"], single_key=True)

    assert result == expected
    rich_ask.assert_not_called()


def test_prompt_single_key_is_case_insensitive_when_requested() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", return_value="B"),
    ):
        result = Prompt.ask(
            "Mode",
            choices=["a", "b", "c"],
            case_sensitive=False,
            single_key=True,
        )

    assert result == "b"


def test_prompt_single_key_enter_accepts_default() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", return_value="\r"),
    ):
        result = Prompt.ask(
            "Mode",
            choices=["a", "b"],
            default="b",
            single_key=True,
        )

    assert result == "b"


def test_prompt_single_key_enter_without_default_keeps_waiting() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", side_effect=["\r", "a"]),
    ):
        result = Prompt.ask("Mode", choices=["a", "b"], single_key=True)

    assert result == "a"


def test_prompt_single_key_ctrl_d_returns_default() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", return_value="\x04"),
    ):
        result = Prompt.ask(
            "Mode",
            choices=["a", "b"],
            default="a",
            single_key=True,
        )

    assert result == "a"


def test_prompt_single_key_ctrl_d_without_default_returns_none() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", return_value="\x04"),
    ):
        result = Prompt.ask("Mode", choices=["a", "b"], single_key=True)

    assert result is None


def test_prompt_single_key_ctrl_c_interrupts() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", return_value="\x03"),
        pytest.raises(KeyboardInterrupt),
    ):
        Prompt.ask("Mode", choices=["a", "b"], single_key=True)


def test_prompt_single_key_ignores_unrelated_keys() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._read_key", side_effect=["x", "b"]),
    ):
        result = Prompt.ask("Mode", choices=["a", "b"], single_key=True)

    assert result == "b"


@pytest.mark.parametrize("choices", [None, ["red", "green"]])
def test_prompt_single_key_requires_single_character_choices(
    choices: list[str] | None,
) -> None:
    with pytest.raises(ValueError, match="one character"):
        Prompt.ask("Mode", choices=choices, single_key=True)


def test_prompt_single_key_rejects_password() -> None:
    with pytest.raises(ValueError, match="password"):
        Prompt.ask(
            "Token",
            choices=["a", "b"],
            password=True,
            single_key=True,
        )


def test_prompt_single_key_falls_back_without_tty() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=False),
        patch("usecli.ui.RichPrompt.ask", return_value="b") as rich_ask,
    ):
        result = Prompt.ask("Mode", choices=["a", "b"], single_key=True)

    assert result == "b"
    rich_ask.assert_called_once()


def test_prompt_int_returns_default_in_json_mode() -> None:
    with (
        runtime.execution_context(json_mode=True),
        patch("usecli.ui.RichIntPrompt.ask") as rich_ask,
    ):
        result = Prompt.ask("Port", type="int", default=8000)

    assert result == 8000
    assert isinstance(result, int)
    rich_ask.assert_not_called()


def test_prompt_int_without_default_raises_in_json_mode() -> None:
    with (
        runtime.execution_context(json_mode=True),
        pytest.raises(NonInteractiveError, match="default"),
    ):
        Prompt.ask("Port", type="int")


def test_prompt_int_delegates_in_normal_mode() -> None:
    with patch("usecli.ui.RichIntPrompt.ask", return_value=42) as rich_ask:
        result = Prompt.ask("Port", type="int", default=8000, show_default=False)

    assert result == 42
    kwargs = rich_ask.call_args.kwargs
    assert kwargs["default"] == 8000
    assert kwargs["show_default"] is False
    assert kwargs["console"] is console


def test_prompt_float_returns_default_in_json_mode() -> None:
    with (
        runtime.execution_context(json_mode=True),
        patch("usecli.ui.RichFloatPrompt.ask") as rich_ask,
    ):
        result = Prompt.ask("Ratio", type="float", default=1)

    assert result == 1.0
    assert isinstance(result, float)
    rich_ask.assert_not_called()


def test_prompt_float_without_default_raises_in_json_mode() -> None:
    with (
        runtime.execution_context(json_mode=True),
        pytest.raises(NonInteractiveError, match="default"),
    ):
        Prompt.ask("Ratio", type="float")


def test_prompt_float_delegates_in_normal_mode() -> None:
    with patch("usecli.ui.RichFloatPrompt.ask", return_value=0.25) as rich_ask:
        result = Prompt.ask("Ratio", type="float", default=0.5)

    assert result == 0.25
    assert rich_ask.call_args.kwargs["default"] == 0.5
    assert rich_ask.call_args.kwargs["console"] is console


def test_prompt_string_rejects_non_string_default() -> None:
    with pytest.raises(TypeError, match="str default"):
        Prompt.ask("Value", default=cast(Any, 1))


def test_prompt_int_rejects_float_default() -> None:
    with pytest.raises(TypeError, match="int default"):
        Prompt.ask("Value", type="int", default=cast(Any, 1.5))


def test_prompt_float_rejects_string_default() -> None:
    with pytest.raises(TypeError, match="float default"):
        Prompt.ask("Value", type="float", default=cast(Any, "1"))


def test_prompt_rejects_unknown_type() -> None:
    ask: Any = Prompt.ask

    with pytest.raises(ValueError, match="type must be"):
        ask("Value", type="bool")


@pytest.mark.parametrize(
    "kwargs",
    [{"password": True}, {"choices": ["a"]}, {"single_key": True}],
)
def test_prompt_non_string_type_rejects_string_only_options(
    kwargs: dict[str, Any],
) -> None:
    ask: Any = Prompt.ask

    with pytest.raises(ValueError, match="type='string'"):
        ask("Value", type="int", **kwargs)


def test_numeric_prompts_are_not_separate_exports() -> None:
    import usecli

    assert "IntPrompt" not in usecli.__all__
    assert "FloatPrompt" not in usecli.__all__
    assert not hasattr(usecli, "IntPrompt")
    assert not hasattr(usecli, "FloatPrompt")


def test_prompt_mask_delegates_to_masked_reader() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._ask_masked", return_value="secret") as ask_masked,
        patch("usecli.ui.RichPrompt.ask") as rich_ask,
    ):
        result = Prompt.ask("Token", mask="*", default="fallback")

    assert result == "secret"
    assert ask_masked.call_args.kwargs["mask"] == "*"
    assert ask_masked.call_args.kwargs["default"] == "fallback"
    rich_ask.assert_not_called()


def test_prompt_mask_falls_back_to_hidden_input_without_tty() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=False),
        patch("usecli.ui.RichPrompt.ask", return_value="secret") as rich_ask,
    ):
        result = Prompt.ask("Token", mask="*")

    assert result == "secret"
    assert rich_ask.call_args.kwargs["password"] is True
    assert "mask" not in rich_ask.call_args.kwargs


def test_prompt_mask_uses_prompt_toolkit_password_processor() -> None:
    class _FakeSession:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def prompt(self, text: Any, **kwargs: Any) -> str:
            self.calls.append({"text": text, **kwargs})
            return "secret"

    session = _FakeSession()
    with patch("usecli.ui._get_masked_session", return_value=session):
        result = _ask_masked("Token", mask="#", default=None, show_default=True)

    assert result == "secret"
    processors = session.calls[0]["input_processors"]
    assert processors[0].char == "#"


def test_prompt_mask_returns_default_for_empty_input() -> None:
    class _EmptySession:
        def prompt(self, text: Any, **kwargs: Any) -> str:
            return ""

    with patch("usecli.ui._get_masked_session", return_value=_EmptySession()):
        assert (
            _ask_masked("Token", mask="*", default="fallback", show_default=True)
            == "fallback"
        )
        assert _ask_masked("Token", mask="*", default=None, show_default=True) is None


def test_get_masked_session_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    from usecli import ui

    monkeypatch.setattr(ui, "_masked_session", None)
    with patch("prompt_toolkit.PromptSession") as session_cls:
        session_cls.return_value = object()
        first = ui._get_masked_session()
        second = ui._get_masked_session()

    assert first is second is session_cls.return_value
    assert session_cls.call_args.kwargs["reserve_space_for_menu"] == 0


def test_prompt_mask_returns_default_in_json_mode() -> None:
    with (
        runtime.execution_context(json_mode=True),
        patch("usecli.ui._ask_masked") as ask_masked,
    ):
        assert Prompt.ask("Token", mask="*", default="fallback") == "fallback"

    ask_masked.assert_not_called()


def test_prompt_mask_requires_one_character() -> None:
    with pytest.raises(ValueError, match="one character"):
        Prompt.ask("Token", mask="**")


def test_prompt_mask_takes_precedence_over_password() -> None:
    with (
        patch("usecli.ui._can_read_single_key", return_value=True),
        patch("usecli.ui._ask_masked", return_value="secret") as ask_masked,
    ):
        result = Prompt.ask("Token", password=True, mask="*")

    assert result == "secret"
    ask_masked.assert_called_once()


@pytest.mark.parametrize("kwargs", [{"choices": ["a"]}, {"single_key": True}])
def test_prompt_mask_rejects_conflicting_options(kwargs: dict[str, Any]) -> None:
    ask: Any = Prompt.ask

    with pytest.raises(ValueError, match="cannot be combined"):
        ask("Token", mask="*", **kwargs)


def test_prompt_mask_requires_string_type() -> None:
    ask: Any = Prompt.ask

    with pytest.raises(ValueError, match="type='string'"):
        ask("Value", type="int", mask="*")
