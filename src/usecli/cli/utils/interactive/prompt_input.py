"""Interactive input for rich prompts that stays put.

rich's ``Console.input`` prints the prompt itself and then calls builtin
``input()`` without one. The system line editor therefore thinks the line
starts at column 0: cursor keys beep or redraw over the prompt and history
lands in the wrong place.

Handing the prompt to ``input()`` fixes that only on GNU readline. macOS uses
libedit, which moves ANSI escapes out of the prompt (dropping the colors) and
still counts their bytes as visible width. prompt_toolkit measures the
rich-rendered prompt itself, so patching ``Console.input`` -- the seam used by
every rich prompt method (``Prompt``, ``Confirm``, ``IntPrompt``, direct
``console.input``) -- gives correct colors, wrapping, cursor keys and history
everywhere.
"""

from __future__ import annotations

import sys
from typing import Any, TextIO

# One session per process so answers can be recalled with the up arrow across
# consecutive prompts. prompt_toolkit is imported lazily: a non-interactive
# invocation must not pay its import cost.
_session: Any = None
_installed = False


def _prompt_session() -> Any:
    """Return the process-wide prompt_toolkit session."""
    global _session
    if _session is None:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory

        # No completion menu is shown, so reserving screen rows for one only
        # forces a cursor-position query some terminals answer slowly or not at
        # all.
        _session = PromptSession(
            history=InMemoryHistory(),
            reserve_space_for_menu=0,
        )
    return _session


def _is_tty(stream: Any) -> bool:
    isatty = getattr(stream, "isatty", None)
    return bool(isatty is not None and isatty())


def _can_prompt_inline(console: Any) -> bool:
    """Return whether prompt_toolkit can own the terminal for this prompt.

    Its renderer reads stdin and writes stdout, so the console must be printing
    to the same stdout: a console aimed elsewhere, redirected output, or a
    piped stdin falls back to rich's own prompt handling.
    """
    stdin = sys.stdin
    stdout = sys.stdout
    if stdin is None or stdout is None:
        return False
    if getattr(console, "file", None) is not stdout:
        return False
    return _is_tty(stdin) and _is_tty(stdout)


def _render_prompt(
    console: Any,
    prompt: Any,
    *,
    markup: bool,
    emoji: bool,
) -> str:
    """Render rich's prompt (markup, styles, emoji) to a single ANSI string.

    ``soft_wrap`` leaves line breaking to prompt_toolkit, which knows the
    terminal width and accounts for the ANSI sequences.
    """
    with console.capture() as capture:
        console.print(prompt, markup=markup, emoji=emoji, end="", soft_wrap=True)
    return capture.get()


def _ask_inline(
    console: Any,
    prompt: Any,
    *,
    markup: bool,
    emoji: bool,
) -> str:
    from prompt_toolkit.formatted_text import ANSI

    rendered = _render_prompt(console, prompt, markup=markup, emoji=emoji)
    return _prompt_session().prompt(ANSI(rendered))


def install_prompt_input() -> None:
    """Patch rich's ``Console.input`` once for correct interactive editing."""
    global _installed
    if _installed:
        return

    from rich.console import Console

    original_input = Console.input

    def prompt_input(
        self: Console,
        prompt: Any = "",
        *,
        markup: bool = True,
        emoji: bool = True,
        password: bool = False,
        stream: TextIO | None = None,
    ) -> str:
        if password or stream is not None or not _can_prompt_inline(self):
            return original_input(
                self,
                prompt,
                markup=markup,
                emoji=emoji,
                password=password,
                stream=stream,
            )
        try:
            return _ask_inline(self, prompt, markup=markup, emoji=emoji)
        except ImportError:  # pragma: no cover - prompt_toolkit always installed
            # A bundle that did not collect prompt_toolkit still gets a usable
            # prompt, just without line editing.
            return original_input(
                self,
                prompt,
                markup=markup,
                emoji=emoji,
                password=password,
                stream=stream,
            )

    _installed = True
    setattr(Console, "input", prompt_input)  # noqa: B010


__all__ = ["install_prompt_input"]
