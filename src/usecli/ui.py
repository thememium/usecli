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


class Confirm:
    """Yes/no confirmation that stays safe in non-interactive runs.

    Delegates to :class:`rich.prompt.Confirm` with the shared :data:`console`.
    In JSON mode it returns ``default`` without reading stdin, so a command
    can keep its confirmation step while producing machine-readable output.

    Example:
        >>> if Confirm.ask("Delete the build directory?", default=False):
        ...     shutil.rmtree("build")
    """

    @staticmethod
    def ask(
        prompt: str,
        *,
        default: bool = True,
    ) -> bool:
        """Ask a yes/no question.

        Args:
            prompt: Question shown to the user.
            default: Answer used when the user submits an empty line, and the
                answer returned without prompting in JSON mode.

        Returns:
            ``True`` for yes, ``False`` for no. In JSON mode this is
            ``default``; in interactive mode it reflects the user's answer.

        Example:
            >>> if Confirm.ask("Do you want to continue?"):
            ...     print("Continuing...")
        """
        if is_json_mode():
            return default
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
