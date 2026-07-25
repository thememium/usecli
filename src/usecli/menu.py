"""Menu component for usecli - wrapper around terminal menu."""

from __future__ import annotations

from typing import TypeVar

from usecli.cli.core.runtime import NonInteractiveError, is_json_mode
from usecli.cli.utils.interactive.terminal_menu import terminal_menu

T = TypeVar("T")


class Menu:
    """Interactive terminal menu for selecting options.

    This is a wrapper around the terminal_menu utility that provides
    a clean interface for displaying interactive menus in the CLI.
    """

    @staticmethod
    def select(
        options: list[T],
        title: str | None = None,
    ) -> T | None:
        """Display a single-select menu.

        Args:
            options: List of items to display in the menu.
            title: Optional title displayed above the menu.

        Returns:
            The selected item, or None if the user cancelled.

        Example:
            >>> choice = Menu.select(
            ...     ["option1", "option2", "option3"],
            ...     title="Pick one:"
            ... )
            >>> if choice:
            ...     print(f"You chose: {choice}")
        """
        if is_json_mode():
            raise NonInteractiveError("Interactive menu is unavailable in JSON mode")
        result = terminal_menu(options, title=title, multi_select=False)
        return result[0] if result else None

    @staticmethod
    def multi_select(
        options: list[T],
        title: str | None = None,
    ) -> list[T]:
        """Display a multi-select menu.

        Args:
            options: List of items to display in the menu.
            title: Optional title displayed above the menu.

        Returns:
            List of selected items (empty if cancelled or nothing selected).

        Example:
            >>> choices = Menu.multi_select(
            ...     ["a", "b", "c"],
            ...     title="Pick many:"
            ... )
            >>> print(f"You chose: {choices}")
        """
        if is_json_mode():
            raise NonInteractiveError("Interactive menu is unavailable in JSON mode")
        return terminal_menu(options, title=title, multi_select=True)


__all__ = ["Menu"]
