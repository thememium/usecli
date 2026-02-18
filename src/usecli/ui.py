"""UI components for usecli - wrappers around Rich components."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm as RichConfirm
from rich.prompt import Prompt as RichPrompt
from rich.table import Table
from rich.text import Text

from usecli.cli.config.colors import COLOR

console = Console()


class Prompt:
    """Wrapper around Rich Prompt for user input."""

    @staticmethod
    def ask(
        prompt: str,
        *,
        default: str | None = None,
        choices: list[str] | None = None,
        show_choices: bool = True,
        show_default: bool = True,
    ) -> str | None:
        """Ask the user for input.

        Args:
            prompt: The prompt text to display.
            default: Default value if user presses Enter without input.
            choices: List of valid choices.
            show_choices: Whether to show choices in prompt.
            show_default: Whether to show default value in prompt.

        Returns:
            The user's input as a string.

        Example:
            >>> name = Prompt.ask("Enter your name")
            >>> choice = Prompt.ask("Pick a color", choices=["red", "green", "blue"])
        """
        return RichPrompt.ask(
            prompt,
            default=default,
            choices=choices,
            show_choices=show_choices,
            show_default=show_default,
            console=console,
        )


class Confirm:
    """Wrapper around Rich Confirm for yes/no prompts."""

    @staticmethod
    def ask(
        prompt: str,
        *,
        default: bool = True,
    ) -> bool:
        """Ask the user for confirmation (yes/no).

        Args:
            prompt: The prompt text to display.
            default: Default value if user presses Enter without input.

        Returns:
            True if user confirmed (yes), False otherwise.

        Example:
            >>> if Confirm.ask("Do you want to continue?"):
            ...     print("Continuing...")
        """
        return RichConfirm.ask(prompt, default=default, console=console)


# Export Rich components directly for advanced use
__all__ = [
    "console",
    "Console",
    "Prompt",
    "Confirm",
    "Table",
    "Panel",
    "Text",
    "box",
    "COLOR",
]
