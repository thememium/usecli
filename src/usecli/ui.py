"""Human-facing UI components shared by usecli commands.

The module wraps a few Rich primitives so command code gets consistent
behavior without importing Rich directly:

* :data:`console` - shared :class:`rich.console.Console` for normal output.
* :class:`Prompt` and :class:`Confirm` - input that degrades safely when the
  CLI runs in JSON mode or without a TTY.
* :class:`Panel`, :class:`Table`, :class:`Text`, and :data:`box` - re-exported
  Rich types for advanced rendering.

Importing this module also installs interactive line editing for every Rich
prompt and ``console.input`` call.
"""

from __future__ import annotations

import sys

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm as RichConfirm
from rich.prompt import Prompt as RichPrompt
from rich.table import Table
from rich.text import Text

from usecli.cli.config.colors import COLOR
from usecli.cli.core.runtime import NonInteractiveError, is_json_mode
from usecli.cli.utils.interactive.prompt_input import install_prompt_input

console: Console = Console()
console.__doc__ = """Shared console for human-facing output.

Write through this console instead of ``print`` so theme colors and JSON-mode
stream routing stay consistent: it resolves ``sys.stdout`` on each write, and
JSON-mode execution redirects stdout to stderr.
"""

# Any rich prompt method (Prompt, Confirm, IntPrompt, console.input) gets
# interactive line editing as soon as the framework's UI module is imported.
install_prompt_input()


class Prompt:
    """Line input that stays safe in non-interactive runs.

    Delegates to :class:`rich.prompt.Prompt` with the shared :data:`console`,
    adding the guarantees CLI commands need:

    * In JSON mode the prompt never reads stdin. It returns ``default``, or
      raises :class:`~usecli.cli.core.runtime.NonInteractiveError` when no
      default was supplied.
    * Interactive line editing is installed for every Rich prompt when this
      module is imported.

    Example:
        >>> name = Prompt.ask("Project name", default="demo")
        >>> color = Prompt.ask("Color", choices=["red", "green", "blue"])
    """

    @staticmethod
    def ask(
        prompt: str,
        *,
        default: str | None = None,
        choices: list[str] | None = None,
        show_choices: bool = True,
        show_default: bool = True,
    ) -> str | None:
        """Ask for a line of text.

        Args:
            prompt: Text shown to the user.
            default: Value returned when the user submits an empty line, and
                the value returned instead of prompting in JSON mode.
            choices: Accepted answers. Rich re-prompts until the response
                matches one of them.
            show_choices: Render the choices after the prompt (``[a/b/c]``).
            show_default: Render the default after the prompt (``[default]``).

        Returns:
            The entered text, or ``default`` when the user accepts it. The
            return value is a string in every path that returns; the ``None``
            in the signature is unreachable because JSON mode with
            ``default=None`` raises instead.

        Raises:
            NonInteractiveError: In JSON mode when ``default`` is ``None``.

        Example:
            >>> name = Prompt.ask("Enter your name")
            >>> choice = Prompt.ask("Pick a color", choices=["red", "green", "blue"])
        """
        if is_json_mode():
            if default is not None:
                return default
            raise NonInteractiveError("Prompt requires a default value in JSON mode")
        return RichPrompt.ask(
            prompt,
            default=default,
            choices=choices,
            show_choices=show_choices,
            show_default=show_default,
            console=console,
        )


def _can_read_single_key() -> bool:
    """Return whether a keypress can be read without waiting for Enter."""
    stdin = sys.stdin
    isatty = getattr(stdin, "isatty", None)
    return bool(isatty is not None and isatty() and console.is_terminal)


def _read_key() -> str:
    """Read one keypress from the terminal without line buffering."""
    if sys.platform == "win32":
        import msvcrt

        return msvcrt.getwch()

    import os
    import termios
    import tty

    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd, termios.TCSADRAIN)
        data = os.read(fd, 1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)
    encoding = getattr(sys.stdin, "encoding", None) or "utf-8"
    return data.decode(encoding, "ignore")


def _ask_single_key(prompt: str, *, default: bool) -> bool:
    """Render a Rich confirm prompt and return on the first valid keypress."""
    prompt_text = RichConfirm(prompt, console=console).make_prompt(default)
    console.print(prompt_text, end="")
    while True:
        key = _read_key()
        if key == "\x03":
            raise KeyboardInterrupt
        if key in ("y", "Y"):
            console.print("y")
            return True
        if key in ("n", "N"):
            console.print("n")
            return False
        if key in ("\r", "\n"):
            console.print("y" if default else "n")
            return default
        if key in ("\x04", ""):
            console.print()
            return default
        # Ignore other keys (arrows, backspace, ...) and keep waiting.


class Confirm:
    """Yes/no confirmation that stays safe in non-interactive runs.

    By default it behaves like :class:`rich.prompt.Confirm`: the answer is
    read as a line, so Enter is required. Pass ``single_key=True`` to answer
    on the first ``y`` or ``n`` keypress instead; Enter alone then accepts
    ``default`` and Ctrl-D does the same.

    Single-key mode only applies when stdin and stdout are terminals. Pipes,
    test runners, and redirected output always fall back to the line-based
    prompt. In JSON mode the method returns ``default`` without reading stdin,
    so a command can keep its confirmation step while producing
    machine-readable output.

    Example:
        >>> if Confirm.ask("Delete the build directory?", default=False):
        ...     shutil.rmtree("build")
        >>> if Confirm.ask("Continue?", single_key=True):
        ...     run_next_step()
    """

    @staticmethod
    def ask(
        prompt: str,
        *,
        default: bool = True,
        single_key: bool = False,
    ) -> bool:
        """Ask a yes/no question.

        Args:
            prompt: Question shown to the user.
            default: Answer used when the user presses Enter without choosing,
                and the answer returned without prompting in JSON mode.
            single_key: Answer on the first ``y`` or ``n`` keypress instead of
                waiting for Enter. Ignored when stdin or stdout is not a
                terminal, and in JSON mode.

        Returns:
            ``True`` for yes, ``False`` for no. In JSON mode this is
            ``default``; in single-key mode it reflects the first valid
            keypress.

        Example:
            >>> if Confirm.ask("Do you want to continue?"):
            ...     print("Continuing...")
            >>> if Confirm.ask("Continue?", single_key=True):
            ...     print("Continuing immediately...")
        """
        if is_json_mode():
            return default
        if single_key and _can_read_single_key():
            return _ask_single_key(prompt, default=default)
        return RichConfirm.ask(prompt, default=default, console=console)


# Export Rich components directly for advanced use
__all__ = [
    "COLOR",
    "Confirm",
    "Console",
    "Panel",
    "Prompt",
    "Table",
    "Text",
    "box",
    "console",
]
