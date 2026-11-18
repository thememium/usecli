"""Terminal menu utility for interactive CLI menus."""

from __future__ import annotations

import shutil
from collections.abc import Callable
from typing import Any, TypeVar, cast

import simple_term_menu
from simple_term_menu import TerminalMenu

from usecli.cli.core.runtime import NonInteractiveError, is_json_mode

T = TypeVar("T")
_PATCHED_SEARCH_LEN = False
_PATCHED_VIM_PAGE_KEYS = False
_PATCHED_VIM_SEARCH = False


def _apply_safe_search_len_patch() -> None:
    global _PATCHED_SEARCH_LEN
    if _PATCHED_SEARCH_LEN:
        return

    def _safe_search_len(self, /) -> int:
        search_text = self._search_text
        if search_text is None:
            return 0
        width = simple_term_menu.wcswidth(search_text)
        return max(width, 0)

    search_class = cast(Any, TerminalMenu.Search)
    search_class.__len__ = _safe_search_len
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
        if key == "J":
            return "down"
        if key == "K":
            return "up"
        return key

    TerminalMenu._read_next_key = _read_next_key_with_vim_page
    _PATCHED_VIM_PAGE_KEYS = True


def _update_vim_search_hint(menu: Any) -> None:
    """Show the retained filter in normal mode.

    simple-term-menu only renders the search line while search input is active.
    This keeps the query visible after ``esc`` so the filter is not silent.
    """
    search_text = menu._search.search_text
    if search_text:
        safe_text = search_text.replace("{", "{{").replace("}", "}}")
        menu._show_search_hint_text = f"filter: {safe_text}   (/ edit · ctrl-u clear)"
    else:
        menu._show_search_hint_text = '(Press "/" to search)'


def _vim_search_key(menu: Any, key: str) -> str:
    """Apply vim search-mode transitions and return the key for the menu loop.

    Returns an empty string (a no-op for the library) when the key only changes
    modes. ``escape`` leaves search input but keeps the filter applied; ``/``
    re-enters input on the same query; ``ctrl-u`` clears the filter.
    """
    search = menu._search
    if getattr(search, "_vim_input_active", False) and search.search_text is None:
        search._vim_input_active = False

    input_active = bool(getattr(search, "_vim_input_active", False))

    if key == "escape":
        if input_active:
            search._vim_input_active = False
            _update_vim_search_hint(menu)
            return ""
        return key

    # simple-term-menu does not map ctrl-u to a codename, so the raw control
    # character is what comes back from the terminal in that case.
    if key in ("ctrl-u", "\x15"):
        if search.search_text is not None:
            search.search_text = None
            search._vim_input_active = False
            _update_vim_search_hint(menu)
        return ""

    if key == "/" and not input_active:
        search._vim_input_active = True
        if search.search_text is None:
            search.search_text = ""
        _update_vim_search_hint(menu)
        return ""

    _update_vim_search_hint(menu)
    return key


def _apply_vim_search_patch() -> None:
    """Let ``escape`` exit search input while keeping the active filter."""
    global _PATCHED_VIM_SEARCH
    if _PATCHED_VIM_SEARCH:
        return

    original_read_next_key = cast(
        Callable[[TerminalMenu, bool], str], TerminalMenu._read_next_key
    )
    search_class = cast(Any, TerminalMenu.Search)
    view_class = cast(Any, TerminalMenu.View)
    original_search_bool = search_class.__bool__
    original_update_view = view_class.update_view

    def _search_bool(self: Any) -> bool:
        input_active = getattr(self, "_vim_input_active", None)
        if input_active is None:
            return original_search_bool(self)
        return bool(input_active and self._search_text is not None)

    def _update_view(self: Any) -> None:
        # The menu loop treats a falsy Search as "normal mode"; the view must
        # still filter on the retained query, so make it truthy just for the
        # duration of the library's own update logic.
        search = self._search
        if getattr(search, "_vim_input_active", None) is False and (
            search.search_text is not None
        ):
            search._vim_input_active = True
            try:
                original_update_view(self)
            finally:
                search._vim_input_active = False
        else:
            original_update_view(self)

    def _read_next_key_with_vim_search(
        self: TerminalMenu, ignore_case: bool = True
    ) -> str:
        key = original_read_next_key(self, ignore_case)
        if getattr(self, "_vim_search_mode", False) is not True:
            return key
        return _vim_search_key(self, key)

    search_class.__bool__ = _search_bool
    view_class.update_view = _update_view
    TerminalMenu._read_next_key = _read_next_key_with_vim_search
    _PATCHED_VIM_SEARCH = True


_apply_safe_search_len_patch()
_apply_vim_page_keys_patch()
_apply_vim_search_patch()


def terminal_menu(
    options: list[T],
    title: str | None = None,
    *,
    multi_select: bool = False,
    search: bool = False,
    search_key: str | None = "/",
    vim_search: bool = False,
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
        vim_search: If True, vim-style search input: escape exits search but
            keeps the filter, ``/`` edits it again and ``ctrl-u`` clears it.
            j/k navigate while search input is inactive.
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
    if is_json_mode():
        raise NonInteractiveError("Interactive menu is unavailable in JSON mode")
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

    if vim_search:
        menu._vim_search_mode = True
        search_obj = getattr(menu, "_search", None)
        if search_obj is not None:
            search_obj._vim_input_active = False
            menu._show_search_hint_text = '(Press "/" to search)'

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
