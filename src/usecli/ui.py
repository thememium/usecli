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
from typing import TYPE_CHECKING, cast, overload

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm as RichConfirm
from rich.prompt import FloatPrompt as RichFloatPrompt
from rich.prompt import IntPrompt as RichIntPrompt
from rich.prompt import Prompt as RichPrompt
from rich.table import Table
from rich.text import Text

from usecli.cli.config.colors import COLOR
from usecli.cli.core.runtime import NonInteractiveError, is_json_mode
from usecli.cli.utils.interactive.prompt_input import install_prompt_input

if TYPE_CHECKING:
    from typing import Any, Literal

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
    """Text, integer, and float input that stays safe in non-interactive runs.

    Delegates to Rich's prompt classes with the shared :data:`console` and
    selects the parser with ``type``:

    * ``"string"`` (default) - :class:`rich.prompt.Prompt`
    * ``"int"`` - :class:`rich.prompt.IntPrompt`
    * ``"float"`` - :class:`rich.prompt.FloatPrompt`

    The wrapper adds the guarantees CLI commands need:

    * In JSON mode the prompt never reads stdin. It returns ``default``, or
      raises :class:`~usecli.cli.core.runtime.NonInteractiveError` when no
      default was supplied.
    * Interactive line editing is installed for every Rich prompt when this
      module is imported.
    * ``single_key=True`` answers single-character choices on one keypress,
      like :meth:`Confirm.ask`.

    Example:
        >>> name = Prompt.ask("Project name", default="demo")
        >>> port = Prompt.ask("Port", type="int", default=8000)
        >>> ratio = Prompt.ask("Ratio", type="float", default=0.5)
        >>> color = Prompt.ask("Color", choices=["red", "green", "blue"])
        >>> token = Prompt.ask("API token", password=True)
        >>> pin = Prompt.ask("PIN", mask="*")
        >>> mode = Prompt.ask("Mode [a/b/c]", choices=["a", "b", "c"], single_key=True)
    """

    @overload
    @staticmethod
    def ask(
        prompt: str,
        *,
        type: Literal["string"] = "string",
        default: str | None = None,
        choices: list[str] | None = None,
        show_choices: bool = True,
        show_default: bool = True,
        password: bool = False,
        mask: str | None = None,
        case_sensitive: bool = True,
        single_key: bool = False,
    ) -> str | None: ...

    @overload
    @staticmethod
    def ask(
        prompt: str,
        *,
        type: Literal["int"],
        default: int | None = None,
        show_default: bool = True,
    ) -> int | None: ...

    @overload
    @staticmethod
    def ask(
        prompt: str,
        *,
        type: Literal["float"],
        default: float | None = None,
        show_default: bool = True,
    ) -> float | None: ...

    @staticmethod
    def ask(
        prompt: str,
        *,
        type: Literal["string", "int", "float"] = "string",
        default: str | float | None = None,
        choices: list[str] | None = None,
        show_choices: bool = True,
        show_default: bool = True,
        password: bool = False,
        mask: str | None = None,
        case_sensitive: bool = True,
        single_key: bool = False,
    ) -> str | int | float | None:
        """Ask for text, an integer, or a float.

        Args:
            prompt: Text shown to the user.
            type: Parser to use: ``"string"`` (default), ``"int"``, or
                ``"float"``.
            default: Value returned when the user submits an empty line, and
                the value returned instead of prompting in JSON mode. Must
                match ``type``.
            choices: Accepted answers. String prompts only; Rich re-prompts
                until the response matches one of them.
            show_choices: Render the choices after the prompt (``[a/b/c]``).
            show_default: Render the default after the prompt (``[default]``).
            password: Hide the typed characters. String prompts only. Ignored
                when ``mask`` is set.
            mask: Echo this character once per typed character instead of the
                real input, for example ``mask="*"``. Takes precedence over
                ``password``. String prompts only, exactly one character, and
                cannot be combined with ``choices`` or ``single_key``. Falls
                back to hidden input when stdin or stdout is not a terminal.
            case_sensitive: Match ``choices`` case-sensitively.
            single_key: Answer on the first keypress instead of waiting for
                Enter. String prompts only, requires ``choices`` where every
                choice is exactly one character, and cannot be combined with
                ``password``. Ignored when stdin or stdout is not a terminal,
                and in JSON mode.

        Returns:
            The parsed value, the matched choice, or ``default``. ``None`` is
            returned only when single-key mode receives Ctrl-D and no
            ``default`` was supplied.

        Raises:
            NonInteractiveError: In JSON mode when ``default`` is ``None``.
            TypeError: When ``default`` does not match ``type``.
            ValueError: When ``password``, ``mask``, ``choices``, or
                ``single_key`` are used with a non-string ``type``, when
                ``mask`` is not one character or conflicts with another
                input option, or when single-key choices are not all single
                characters.

        Example:
            >>> name = Prompt.ask("Enter your name")
            >>> port = Prompt.ask("Port", type="int", default=8000)
            >>> token = Prompt.ask("Token", mask="*")
            >>> mode = Prompt.ask("Mode [a/b/c]", choices=["a", "b", "c"], single_key=True)
        """
        if type not in ("string", "int", "float"):
            raise ValueError("type must be 'string', 'int', or 'float'")
        if type != "string":
            if password:
                raise ValueError("password requires type='string'")
            if choices is not None:
                raise ValueError("choices requires type='string'")
            if single_key:
                raise ValueError("single_key requires type='string'")
            if mask is not None:
                raise ValueError("mask requires type='string'")

        if mask is not None:
            if len(mask) != 1:
                raise ValueError("mask must be exactly one character")
            if choices is not None:
                raise ValueError("mask cannot be combined with choices")
            if single_key:
                raise ValueError("mask cannot be combined with single_key")

        if type == "string":
            if default is not None and not isinstance(default, str):
                raise TypeError("type='string' requires a str default")
        elif type == "int":
            if default is not None and (
                isinstance(default, bool) or not isinstance(default, int)
            ):
                raise TypeError("type='int' requires an int default")
        else:
            if default is not None and (
                isinstance(default, bool) or not isinstance(default, (int, float))
            ):
                raise TypeError("type='float' requires a float default")
            if default is not None:
                default = float(default)

        if single_key:
            if password:
                raise ValueError("single_key cannot be combined with password")
            if not choices or any(len(choice) != 1 for choice in choices):
                raise ValueError(
                    "single_key requires choices with exactly one character each"
                )

        if is_json_mode():
            if default is not None:
                return default
            raise NonInteractiveError("Prompt requires a default value in JSON mode")

        if type == "int":
            return RichIntPrompt.ask(
                prompt,
                default=cast("int | None", default),
                show_default=show_default,
                console=console,
            )
        if type == "float":
            return RichFloatPrompt.ask(
                prompt,
                default=cast("float | None", default),
                show_default=show_default,
                console=console,
            )
        if mask is not None:
            if _can_read_single_key():
                return _ask_masked(
                    prompt,
                    mask=mask,
                    default=cast("str | None", default),
                    show_default=show_default,
                )
            return RichPrompt.ask(
                prompt,
                default=cast("str | None", default),
                show_default=show_default,
                password=True,
                console=console,
            )
        if single_key and _can_read_single_key():
            return _ask_single_choice(
                prompt,
                choices=choices or [],
                default=cast("str | None", default),
                case_sensitive=case_sensitive,
                show_choices=show_choices,
                show_default=show_default,
            )
        return RichPrompt.ask(
            prompt,
            default=cast("str | None", default),
            choices=choices,
            show_choices=show_choices,
            show_default=show_default,
            password=password,
            case_sensitive=case_sensitive,
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


_masked_session: Any = None


def _get_masked_session() -> Any:
    """Return a prompt_toolkit session that never stores input in history."""
    global _masked_session
    if _masked_session is None:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import DummyHistory

        _masked_session = PromptSession(
            history=DummyHistory(),
            reserve_space_for_menu=0,
        )
    return _masked_session


def _ask_masked(
    prompt: str,
    *,
    mask: str,
    default: str | None,
    show_default: bool,
) -> str | None:
    """Render a Rich prompt and echo ``mask`` for every typed character."""
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.layout.processors import PasswordProcessor

    prompt_text = RichPrompt(
        prompt,
        console=console,
        show_default=show_default,
    ).make_prompt(default)
    with console.capture() as capture:
        console.print(prompt_text, end="", soft_wrap=True)
    value = _get_masked_session().prompt(
        ANSI(capture.get()),
        input_processors=[PasswordProcessor(mask)],
    )
    return value if value else default


def _ask_single_choice(
    prompt: str,
    *,
    choices: list[str],
    default: str | None,
    case_sensitive: bool,
    show_choices: bool,
    show_default: bool,
) -> str | None:
    """Render a Rich choice prompt and return on the first valid keypress."""
    prompt_text = RichPrompt(
        prompt,
        console=console,
        choices=choices,
        case_sensitive=case_sensitive,
        show_choices=show_choices,
        show_default=show_default,
    ).make_prompt(default)
    console.print(prompt_text, end="")
    while True:
        key = _read_key()
        if key == "\x03":
            raise KeyboardInterrupt
        if key in ("\r", "\n"):
            if default is None:
                continue
            console.print(default, markup=False)
            return default
        if key in ("\x04", ""):
            console.print()
            return default
        for choice in choices:
            if choice == key or (not case_sensitive and choice.lower() == key.lower()):
                console.print(choice, markup=False)
                return choice
        # Ignore other keys (arrows, backspace, ...) and keep waiting.


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
