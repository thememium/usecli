"""Terminal menu utility for interactive CLI menus."""

from __future__ import annotations

from typing import Callable, TypeVar

from simple_term_menu import TerminalMenu

T = TypeVar("T")


def terminal_menu(
    options: list[T],
    title: str | None = None,
    *,
    multi_select: bool = False,
    search: bool = False,
    search_key: str | None = "/",
    show_search_hint: bool = True,
    status_bar: str | None = None,
    preview_command: Callable[[str], str] | str | None = None,
    preview_size: float | None = 0.70,
) -> list[T]:
    """Display an interactive terminal menu.

    Args:
        options: List of items to display in the menu.
        title: Optional title displayed above the menu.
        multi_select: If True, allow selecting multiple items with spacebar.
                     If False, only single selection allowed.
        search: If True, enable interactive search.
        search_key: Key to activate search. Use None to search on any letter key.
        show_search_hint: If True, show the search hint text when search is enabled.
        status_bar: Optional status bar text shown below the menu.
        preview_command: Optional preview command or callable to render a preview.
        preview_size: Optional preview size as a fraction of terminal height.

    Returns:
        List of selected items (empty if cancelled or nothing selected).
        - Single select: Returns list with one item, or empty list if cancelled.
        - Multi select: Returns list with all selected items, or empty list.

    Example:
        >>> # Single select
        >>> choices = show_menu(["option1", "option2", "option3"], title="Pick one:")
        >>> if choices:
        ...     print(f"You chose: {choices[0]}")
        >>>
        >>> # Multi select
        >>> choices = show_menu(["a", "b", "c"], title="Pick many:", multi_select=True)
        >>> print(f"You chose: {choices}")
    """
    if not options:
        return []

    # Convert options to strings for display
    display_options = [str(opt) for opt in options]

    preview_size_value: float = 0.25
    if preview_command is not None:
        preview_size_value = preview_size if preview_size is not None else 0.25

    menu = TerminalMenu(
        display_options,
        title=title,
        multi_select=multi_select,
        show_multi_select_hint=multi_select,
        menu_cursor_style=("fg_cyan", "bold"),
        menu_highlight_style=("bg_cyan", "fg_black"),
        status_bar_style=("fg_cyan", "bold"),
        multi_select_cursor_style=("fg_cyan", "bold"),
        multi_select_select_on_accept=False,
        multi_select_empty_ok=True,
        status_bar=status_bar,
        search_key=search_key if search else "/",
        show_search_hint=show_search_hint if search else False,
        preview_command=preview_command,
        preview_size=preview_size_value,
    )

    result = menu.show()

    # Handle different return types from TerminalMenu
    if result is None:
        # User cancelled (Ctrl+C or Escape)
        return []

    if multi_select:
        if isinstance(result, int):
            # Single selection in multi-select mode shouldn't happen,
            # but handle it gracefully
            return [options[result]]
        elif isinstance(result, tuple):
            # Multi-select result - empty tuple means nothing selected
            return [options[idx] for idx in result]
        else:
            return []
    else:
        if isinstance(result, int):
            return [options[result]]
        return []
