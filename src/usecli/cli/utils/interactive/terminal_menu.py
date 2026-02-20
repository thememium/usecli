"""Terminal menu utility for interactive CLI menus."""

from __future__ import annotations

import shutil
from typing import Any, Callable, TypeVar, cast

import simple_term_menu
from simple_term_menu import TerminalMenu

T = TypeVar("T")
_PATCHED_SEARCH_LEN = False
_PATCHED_VIM_PAGE_KEYS = False


def _apply_safe_search_len_patch() -> None:
    global _PATCHED_SEARCH_LEN
    if _PATCHED_SEARCH_LEN:
        return

    def _safe_search_len(self, /) -> int:
        search_text = self._search_text
        if search_text is None:
            return 0
        width = simple_term_menu.wcswidth(search_text)
        return width if width >= 0 else 0

    search_class = cast(Any, TerminalMenu.Search)
    setattr(search_class, "__len__", _safe_search_len)
    _PATCHED_SEARCH_LEN = True


def _apply_vim_page_keys_patch() -> None:
    global _PATCHED_VIM_PAGE_KEYS
    if _PATCHED_VIM_PAGE_KEYS:
        return

    original_read_next_key = cast(
        Callable[[TerminalMenu, bool], str], TerminalMenu._read_next_key
    )

    def _read_next_key_with_vim_page(
        self: TerminalMenu, ignore_case: bool = True
    ) -> str:
        key = original_read_next_key(self, ignore_case)
        if getattr(self, "_search", False):
            return key
        if getattr(self, "_search_key", None) is None:
            return key
        if key in ("d", "D"):
            return "page_down"
        if key in ("u", "U"):
            return "page_up"
        return key

    setattr(TerminalMenu, "_read_next_key", _read_next_key_with_vim_page)
    _PATCHED_VIM_PAGE_KEYS = True


_apply_safe_search_len_patch()
_apply_vim_page_keys_patch()


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
    clear_screen: bool | None = None,
    clear_menu_on_exit: bool | None = None,
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

    preview_command_value = preview_command
    preview_size_value = 0.25
    if preview_command is not None:
        terminal_lines = shutil.get_terminal_size((80, 24)).lines
        title_lines_count = 0
        if isinstance(title, str):
            title_lines_count = len(title.split("\n"))
        elif title is not None:
            title_lines_count = len(tuple(title))

        status_bar_lines_count = 0
        if isinstance(status_bar, str):
            status_bar_lines_count = len(status_bar.split("\n"))
        elif callable(status_bar):
            status_bar_lines_count = 1
        elif status_bar is not None:
            status_bar_lines_count = len(tuple(status_bar))

        search_lines_count = 1 if search else 0
        min_menu_lines = 5
        available_preview_lines = max(
            0,
            terminal_lines
            - (
                title_lines_count
                + status_bar_lines_count
                + search_lines_count
                + min_menu_lines
            ),
        )

        if available_preview_lines < 3 or terminal_lines <= 0:
            preview_command_value = None
            preview_size_value = 0.25
        else:
            max_preview_size = available_preview_lines / terminal_lines
            preview_size_value = min(
                preview_size if preview_size is not None else 0.25,
                max_preview_size,
            )
    search_key_value = search_key if search else "/"
    show_search_hint_value = show_search_hint if search else False
    clear_screen_value = clear_screen if clear_screen is not None else False
    clear_menu_on_exit_value = (
        clear_menu_on_exit if clear_menu_on_exit is not None else True
    )

    terminal_menu_class = cast(Any, TerminalMenu)
    menu = terminal_menu_class(
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
        search_key=search_key_value,
        show_search_hint=show_search_hint_value,
        preview_command=preview_command_value,
        preview_size=preview_size_value,
        clear_screen=clear_screen_value,
        clear_menu_on_exit=clear_menu_on_exit_value,
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
