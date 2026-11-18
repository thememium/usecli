"""Comprehensive tests for terminal_menu function."""

import importlib
import os
from unittest.mock import MagicMock, Mock, patch

import pytest

# Import the function to test
from usecli.cli.utils.interactive.terminal_menu import terminal_menu


def _set_vim_input_active(search, active):
    """Set the runtime flag the vim-search patch adds to Search instances."""
    attr = "_vim_input_active"
    setattr(search, attr, active)


def _vim_input_active(search):
    """Read the runtime flag the vim-search patch adds to Search instances."""
    attr = "_vim_input_active"
    return getattr(search, attr)


class TestTerminalMenuEmptyOptions:
    """Test cases for terminal_menu with empty options list."""

    def test_empty_options_returns_empty_list(self):
        """Test that empty options list returns empty list without creating menu."""
        result = terminal_menu([])
        assert result == []
        assert isinstance(result, list)

    def test_empty_options_with_title_returns_empty_list(self):
        """Test that empty options list returns empty list even with title."""
        result = terminal_menu([], title="Select an option")
        assert result == []

    def test_empty_options_with_multi_select_returns_empty_list(self):
        """Test that empty options list returns empty list in multi_select mode."""
        result = terminal_menu([], multi_select=True)
        assert result == []


class TestTerminalMenuSingleSelectMode:
    """Test cases for terminal_menu in single select mode (default)."""

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_select_with_int_result(self, mock_menu_class):
        """Test single select mode when menu.show() returns an int."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 1
        mock_menu_class.return_value = mock_menu_instance

        options = ["Option A", "Option B", "Option C"]
        result = terminal_menu(options)

        assert result == ["Option B"]
        assert len(result) == 1
        mock_menu_instance.show.assert_called_once()

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_select_first_option(self, mock_menu_class):
        """Test selecting first option returns first item."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["First", "Second", "Third"])
        assert result == ["First"]

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_select_last_option(self, mock_menu_class):
        """Test selecting last option returns last item."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 2
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["First", "Second", "Third"])
        assert result == ["Third"]

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_select_cancel_returns_empty_list(self, mock_menu_class):
        """Test that pressing cancel (None) returns empty list."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = None
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["Option A", "Option B"])
        assert result == []

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_select_with_title(self, mock_menu_class):
        """Test that title is passed to TerminalMenu."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["Option 1", "Option 2"], title="Select your choice")

        assert result == ["Option 1"]
        call_kwargs = mock_menu_class.call_args.kwargs
        assert call_kwargs.get("title") == "Select your choice"

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_select_with_non_string_options(self, mock_menu_class):
        """Test single select with integer options."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 1
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu([10, 20, 30])

        assert result == [20]
        call_args = mock_menu_class.call_args[0][0]
        assert call_args == ["10", "20", "30"]

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_select_with_tuple_result_returns_empty(self, mock_menu_class):
        """Test single select mode with tuple result returns empty."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = (0, 1)
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["Option A", "Option B", "Option C"], multi_select=False)
        assert result == []


class TestTerminalMenuMultiSelectMode:
    """Test cases for terminal_menu in multi-select mode."""

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_with_single_int_result(self, mock_menu_class):
        """Test multi select when menu.show() returns single int."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 1
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["Option A", "Option B", "Option C"], multi_select=True)
        assert result == ["Option B"]
        assert len(result) == 1

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_with_tuple_result(self, mock_menu_class):
        """Test multi select when menu.show() returns tuple of indices."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = (0, 2)
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["Option A", "Option B", "Option C"], multi_select=True)
        assert result == ["Option A", "Option C"]
        assert len(result) == 2

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_with_multiple_items(self, mock_menu_class):
        """Test multi select with three items selected."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = (0, 1, 2)
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["First", "Second", "Third"], multi_select=True)
        assert result == ["First", "Second", "Third"]
        assert len(result) == 3

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_cancel_returns_empty_list(self, mock_menu_class):
        """Test that canceling multi select returns empty list."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = None
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["Option A", "Option B", "Option C"], multi_select=True)
        assert result == []

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_no_selection_returns_empty_list(self, mock_menu_class):
        """Test multi select with empty tuple returns empty list."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = ()
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["Option A", "Option B"], multi_select=True)
        assert result == []

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_with_title(self, mock_menu_class):
        """Test that multi_select_hint is shown when multi_select=True."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = (0, 1)
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(
            ["A", "B", "C"], title="Select multiple items", multi_select=True
        )

        assert result == ["A", "B"]
        call_kwargs = mock_menu_class.call_args.kwargs
        assert call_kwargs.get("multi_select") is True
        assert call_kwargs.get("show_multi_select_hint") is True

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_invalid_return_type(self, mock_menu_class):
        """Test multi select with invalid return type returns empty."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = "invalid"
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["Option A", "Option B"], multi_select=True)
        assert result == []


class TestTerminalMenuMenuConfiguration:
    """Test cases for TerminalMenu configuration."""

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_menu_styling_configuration(self, mock_menu_class):
        """Test that all styling parameters are passed to TerminalMenu."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        terminal_menu(["A", "B"])
        call_kwargs = mock_menu_class.call_args.kwargs

        assert call_kwargs["menu_cursor_style"] == ("usecli_primary", "bold")
        assert call_kwargs["menu_highlight_style"] == (
            "usecli_bg_primary",
            "usecli_background",
            "bold",
        )
        assert call_kwargs["search_highlight_style"] == (
            "usecli_bg_accent",
            "usecli_background",
            "bold",
        )
        assert call_kwargs["status_bar_style"] == (
            "usecli_dim",
            "usecli_foreground",
        )
        assert call_kwargs["multi_select_cursor_style"] == (
            "usecli_primary",
            "bold",
        )
        assert call_kwargs["multi_select_cursor_brackets_style"] == ("usecli_muted",)

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_options_configuration(self, mock_menu_class):
        """Test multi select specific options are set correctly."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        terminal_menu(["A", "B"], multi_select=True)
        call_kwargs = mock_menu_class.call_args.kwargs

        assert call_kwargs["multi_select_select_on_accept"] is False
        assert call_kwargs["multi_select_empty_ok"] is True

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_display_options_are_strings(self, mock_menu_class):
        """Test that display options are converted to strings."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        terminal_menu([1, 2, 3])
        display_options = mock_menu_class.call_args[0][0]
        assert display_options == ["1", "2", "3"]
        assert all(isinstance(opt, str) for opt in display_options)

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_search_and_preview_configuration(self, mock_menu_class):
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        def preview_command(value: str) -> str:
            return f"Preview:\n{value}\n"

        status_bar = "Enter = select • Esc = quit"

        with patch(
            "usecli.cli.utils.interactive.terminal_menu.shutil.get_terminal_size"
        ) as mock_terminal_size:
            mock_terminal_size.return_value = os.terminal_size((120, 60))
            terminal_menu(
                ["Option A", "Option B"],
                search=True,
                search_key=None,
                show_search_hint=True,
                status_bar=status_bar,
                preview_command=preview_command,
                preview_size=0.70,
            )

        call_kwargs = mock_menu_class.call_args.kwargs
        assert call_kwargs["search_key"] is None
        assert call_kwargs["show_search_hint"] is True
        assert call_kwargs["status_bar"] == status_bar
        assert call_kwargs["preview_command"] is preview_command
        assert call_kwargs["preview_size"] == 0.70


class TestTerminalMenuEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_option_list(self, mock_menu_class):
        """Test with only one option."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["Only Option"])
        assert result == ["Only Option"]

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_large_list_of_options(self, mock_menu_class):
        """Test with large number of options."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 99
        mock_menu_class.return_value = mock_menu_instance

        options = [f"Option {i}" for i in range(100)]
        result = terminal_menu(options)
        assert result == ["Option 99"]

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_options_with_special_characters(self, mock_menu_class):
        """Test options containing special characters."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 1
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["Option 🎯", "Option ✓", "Option ✗"])
        assert result == ["Option ✓"]

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_options_with_empty_strings(self, mock_menu_class):
        """Test options including empty strings."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["", "Non-empty", ""])
        assert result == [""]

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_options_with_whitespace(self, mock_menu_class):
        """Test options with various whitespace."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 1
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(["  spaces  ", "\ttabs\t", "\nnewline\n"])
        assert result == ["\ttabs\t"]


class TestTerminalMenuTypeGeneric:
    """Test that the TypeVar T works correctly."""

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_return_type_preserves_option_type(self, mock_menu_class):
        """Test that returned items preserve original type."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        class CustomType:
            def __init__(self, value):
                self.value = value

        obj = CustomType(42)
        result = terminal_menu([obj])
        assert result == [obj]
        assert result[0].value == 42

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_preserves_types(self, mock_menu_class):
        """Test that multi-select preserves original types."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = (0, 1, 2)
        mock_menu_class.return_value = mock_menu_instance

        class Item:
            def __init__(self, id):
                self.id = id

        items = [Item(1), Item(2), Item(3)]
        result = terminal_menu(items, multi_select=True)

        assert len(result) == 3
        assert all(isinstance(item, Item) for item in result)
        assert [item.id for item in result] == [1, 2, 3]


class TestTerminalMenuIntegration:
    """Integration tests combining multiple features."""

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_full_workflow_single_select_with_title(self, mock_menu_class):
        """Test complete single select workflow with title."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 1
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(
            ["Choice 1", "Choice 2", "Choice 3"],
            title="Select an option",
            multi_select=False,
        )
        assert result == ["Choice 2"]
        call_kwargs = mock_menu_class.call_args.kwargs
        assert call_kwargs["title"] == "Select an option"
        assert call_kwargs["multi_select"] is False

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_full_workflow_multi_select_with_title(self, mock_menu_class):
        """Test complete multi-select workflow with title."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = (0, 2)
        mock_menu_class.return_value = mock_menu_instance

        result = terminal_menu(
            ["Option A", "Option B", "Option C"],
            title="Select multiple options",
            multi_select=True,
        )
        assert result == ["Option A", "Option C"]
        call_kwargs = mock_menu_class.call_args.kwargs
        assert call_kwargs["title"] == "Select multiple options"
        assert call_kwargs["multi_select"] is True
        assert call_kwargs["show_multi_select_hint"] is True

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_sequential_calls_independent(self, mock_menu_class):
        """Test that sequential calls to terminal_menu are independent."""
        mock_menu_instance1 = Mock()
        mock_menu_instance1.show.return_value = 0
        mock_menu_instance2 = Mock()
        mock_menu_instance2.show.return_value = 1
        mock_menu_class.side_effect = [mock_menu_instance1, mock_menu_instance2]

        result1 = terminal_menu(["A", "B"])
        result2 = terminal_menu([1, 2, 3], multi_select=True)

        assert result1 == ["A"]
        assert result2 == [2]
        assert mock_menu_class.call_count == 2

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_clear_screen_defaults(self, mock_menu_class):
        """Test clear_screen and clear_menu_on_exit defaults."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        terminal_menu(["A", "B"])
        call_kwargs = mock_menu_class.call_args.kwargs

        assert call_kwargs["clear_screen"] is False
        assert call_kwargs["clear_menu_on_exit"] is True

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_clear_screen_custom_values(self, mock_menu_class):
        """Test clear_screen and clear_menu_on_exit custom values."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        terminal_menu(["A", "B"], clear_screen=True, clear_menu_on_exit=False)
        call_kwargs = mock_menu_class.call_args.kwargs

        assert call_kwargs["clear_screen"] is True
        assert call_kwargs["clear_menu_on_exit"] is False

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_preview_command_with_callable(self, mock_menu_class):
        """Test preview_command with a callable."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        def preview(value: str) -> str:
            return f"Preview: {value}"

        with patch(
            "usecli.cli.utils.interactive.terminal_menu.shutil.get_terminal_size"
        ) as mock_size:
            mock_size.return_value = os.terminal_size((80, 40))
            terminal_menu(["A", "B"], preview_command=preview, preview_size=0.5)

        call_kwargs = mock_menu_class.call_args.kwargs
        assert call_kwargs["preview_command"] is preview

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_preview_command_disabled_when_small_terminal(self, mock_menu_class):
        """Test preview_command is disabled when terminal is too small."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        def preview(value: str) -> str:
            return f"Preview: {value}"

        with patch(
            "usecli.cli.utils.interactive.terminal_menu.shutil.get_terminal_size"
        ) as mock_size:
            mock_size.return_value = os.terminal_size((80, 5))
            terminal_menu(["A", "B"], preview_command=preview)

        call_kwargs = mock_menu_class.call_args.kwargs
        # Preview should be disabled for small terminals
        assert call_kwargs["preview_command"] is None

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_search_disabled_by_default(self, mock_menu_class):
        """Test search is disabled by default."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        terminal_menu(["A", "B"])
        call_kwargs = mock_menu_class.call_args.kwargs

        assert call_kwargs["search_key"] == "/"
        assert call_kwargs["show_search_hint"] is False

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_search_enabled(self, mock_menu_class):
        """Test search enabled with custom key."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        terminal_menu(["A", "B"], search=True, search_key="?", show_search_hint=True)
        call_kwargs = mock_menu_class.call_args.kwargs

        assert call_kwargs["search_key"] == "?"
        assert call_kwargs["show_search_hint"] is True

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_search_with_none_key(self, mock_menu_class):
        """Test search with None key (search on any letter)."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        terminal_menu(["A", "B"], search=True, search_key=None)
        call_kwargs = mock_menu_class.call_args.kwargs

        assert call_kwargs["search_key"] is None

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_preview_with_tuple_title(self, mock_menu_class):
        """Test preview command with tuple title."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        def preview(value: str) -> str:
            return f"Preview: {value}"

        with patch(
            "usecli.cli.utils.interactive.terminal_menu.shutil.get_terminal_size"
        ) as mock_size:
            mock_size.return_value = os.terminal_size((80, 40))
            terminal_menu(["A", "B"], title=("line1", "line2"), preview_command=preview)  # type: ignore[ty:invalid-argument-type]

        call_kwargs = mock_menu_class.call_args.kwargs
        assert call_kwargs["preview_command"] is preview

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_preview_with_string_title(self, mock_menu_class):
        """Test preview command with string title (multi-line)."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        def preview(value: str) -> str:
            return f"Preview: {value}"

        with patch(
            "usecli.cli.utils.interactive.terminal_menu.shutil.get_terminal_size"
        ) as mock_size:
            mock_size.return_value = os.terminal_size((80, 40))
            terminal_menu(["A", "B"], title="Line 1\nLine 2", preview_command=preview)

        call_kwargs = mock_menu_class.call_args.kwargs
        assert call_kwargs["preview_command"] is preview

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_preview_with_callable_status_bar(self, mock_menu_class):
        """Test preview command with callable status bar."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        def preview(value: str) -> str:
            return f"Preview: {value}"

        def status_bar_getter(value: str) -> str:
            return f"Status: {value}"

        with patch(
            "usecli.cli.utils.interactive.terminal_menu.shutil.get_terminal_size"
        ) as mock_size:
            mock_size.return_value = os.terminal_size((80, 40))
            terminal_menu(
                ["A", "B"],
                status_bar=status_bar_getter,  # type: ignore[ty:invalid-argument-type]
                preview_command=preview,
            )

        call_kwargs = mock_menu_class.call_args.kwargs
        assert call_kwargs["status_bar"] is status_bar_getter

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_preview_with_tuple_status_bar(self, mock_menu_class):
        """Test preview command with tuple status bar."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        def preview(value: str) -> str:
            return f"Preview: {value}"

        with patch(
            "usecli.cli.utils.interactive.terminal_menu.shutil.get_terminal_size"
        ) as mock_size:
            mock_size.return_value = os.terminal_size((80, 40))
            terminal_menu(
                ["A", "B"],
                status_bar=("line1", "line2"),  # type: ignore[ty:invalid-argument-type]
                preview_command=preview,
            )

        call_kwargs = mock_menu_class.call_args.kwargs
        assert call_kwargs["status_bar"] == ("line1", "line2")


# =============================================================================
# Coverage-focused: terminal_menu safe-search-length and vim page-key patches
# =============================================================================

# NOTE: `import usecli.cli.utils.interactive.terminal_menu as tm` would bind the
# `terminal_menu` *function* (re-exported by the package __init__), so we import
# the module object explicitly.
tm = importlib.import_module("usecli.cli.utils.interactive.terminal_menu")


class TestSafeSearchLenPatch:
    def test_patch_is_idempotent(self):
        """Calling the patch again returns immediately (line 22)."""
        tm._apply_safe_search_len_patch()

    def test_search_len_with_text(self):
        """len() on a Search with text returns the display width (lines 28-29)."""
        search = tm.TerminalMenu.Search(["a", "b"], search_text="abc")
        assert len(search) == 3

    def test_search_len_with_none(self):
        """len() on a Search with no text returns 0 (line 27)."""
        search = tm.TerminalMenu.Search(["a", "b"])
        assert len(search) == 0


class TestVimPageKeysPatch:
    def test_patch_is_idempotent(self):
        """Calling the patch again returns immediately (line 39)."""
        tm._apply_vim_page_keys_patch()

    def _make_menu(self, search=False, search_key="/"):
        menu = MagicMock()
        menu._terminal_code_to_codename = {}
        menu._tty_in = MagicMock()
        menu._tty_in.fileno.return_value = 0
        menu._reading_next_key = False
        menu._paint_before_next_read = False
        menu._paint_menu = MagicMock()
        menu._search = search
        menu._search_key = search_key
        return menu

    def _call(self, menu, key_bytes, ignore_case=True):
        with patch("simple_term_menu.os.read", return_value=key_bytes):
            return tm.TerminalMenu._read_next_key(menu, ignore_case)

    def test_d_maps_to_page_down(self):
        menu = self._make_menu()
        assert self._call(menu, b"d") == "page_down"

    def test_u_maps_to_page_up(self):
        menu = self._make_menu()
        assert self._call(menu, b"u") == "page_up"

    def test_uppercase_j_maps_to_down(self):
        menu = self._make_menu()
        assert self._call(menu, b"J", ignore_case=False) == "down"

    def test_uppercase_k_maps_to_up(self):
        menu = self._make_menu()
        assert self._call(menu, b"K", ignore_case=False) == "up"

    def test_other_key_returned_unchanged(self):
        menu = self._make_menu()
        assert self._call(menu, b"x") == "x"

    def test_search_active_returns_key_unchanged(self):
        menu = self._make_menu(search=True)
        assert self._call(menu, b"d") == "d"

    def test_no_search_key_returns_key_unchanged(self):
        menu = self._make_menu(search_key=None)
        assert self._call(menu, b"d") == "d"


class TestVimSearchSetting:
    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_vim_search_configures_menu(self, mock_menu_class):
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_instance._search = Mock()
        mock_menu_class.return_value = mock_menu_instance

        terminal_menu(["A", "B"], vim_search=True)

        assert mock_menu_instance._vim_search_mode is True
        assert mock_menu_instance._search._vim_input_active is False
        assert mock_menu_instance._show_search_hint_text == '(Press "/" to search)'

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_vim_search_without_search_object(self, mock_menu_class):
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_instance._search = None
        mock_menu_class.return_value = mock_menu_instance

        terminal_menu(["A", "B"], vim_search=True)

        assert mock_menu_instance._vim_search_mode is True


class TestVimSearchState:
    def _make_menu(self, text=None, input_active=False):
        menu = MagicMock()
        menu._search = tm.TerminalMenu.Search(["about", "help"], search_text=text)
        _set_vim_input_active(menu._search, input_active)
        menu._show_search_hint_text = ""
        return menu

    def test_search_bool_without_vim_flag_uses_library_semantics(self):
        search = tm.TerminalMenu.Search(["a"], search_text="a")
        assert bool(search) is True

    def test_search_bool_tracks_vim_input_mode(self):
        search = tm.TerminalMenu.Search(["a"], search_text="a")
        _set_vim_input_active(search, False)
        assert bool(search) is False
        _set_vim_input_active(search, True)
        assert bool(search) is True

    def test_search_bool_is_false_without_text(self):
        search = tm.TerminalMenu.Search(["a"])
        _set_vim_input_active(search, True)
        assert bool(search) is False

    def test_view_still_filters_with_retained_query(self):
        view = MagicMock()
        view._search = tm.TerminalMenu.Search(["about", "help"], search_text="help")
        _set_vim_input_active(view._search, False)
        view._menu_entries = ["about", "help"]
        view._viewport = MagicMock()

        tm.TerminalMenu.View.update_view(view)

        assert view._displayed_index_to_menu_index == (1,)
        assert _vim_input_active(view._search) is False

    def test_view_shows_all_entries_without_query(self):
        view = MagicMock()
        view._search = tm.TerminalMenu.Search(["about", "help"])
        _set_vim_input_active(view._search, False)
        view._menu_entries = ["about", "help"]
        view._viewport = MagicMock()

        tm.TerminalMenu.View.update_view(view)

        assert view._displayed_index_to_menu_index == (0, 1)


class TestVimSearchKeys:
    def test_patch_is_idempotent(self):
        tm._apply_vim_search_patch()

    def _make_menu(self, text=None, input_active=False):
        menu = MagicMock()
        menu._search = tm.TerminalMenu.Search(["about", "help"], search_text=text)
        _set_vim_input_active(menu._search, input_active)
        menu._show_search_hint_text = ""
        return menu

    def test_slash_starts_search(self):
        menu = self._make_menu()
        assert tm._vim_search_key(menu, "/") == ""
        assert menu._search.search_text == ""
        assert menu._search._vim_input_active is True
        assert "Press" in menu._show_search_hint_text

    def test_slash_reuses_retained_filter(self):
        menu = self._make_menu(text="help")
        assert tm._vim_search_key(menu, "/") == ""
        assert menu._search.search_text == "help"
        assert menu._search._vim_input_active is True
        assert "filter: help" in menu._show_search_hint_text
        assert "/ edit" in menu._show_search_hint_text

    def test_slash_while_searching_is_typed(self):
        menu = self._make_menu(text="", input_active=True)
        assert tm._vim_search_key(menu, "/") == "/"

    def test_escape_exits_search_and_keeps_filter(self):
        menu = self._make_menu(text="insp", input_active=True)
        assert tm._vim_search_key(menu, "escape") == ""
        assert menu._search.search_text == "insp"
        assert menu._search._vim_input_active is False
        assert "filter: insp" in menu._show_search_hint_text

    def test_escape_in_normal_mode_quits(self):
        menu = self._make_menu(text="insp", input_active=False)
        assert tm._vim_search_key(menu, "escape") == "escape"
        assert menu._search.search_text == "insp"

    def test_enter_exits_search_and_keeps_filter(self):
        menu = self._make_menu(text="insp", input_active=True)
        assert tm._vim_search_key(menu, "enter") == ""
        assert menu._search.search_text == "insp"
        assert menu._search._vim_input_active is False
        assert "filter: insp" in menu._show_search_hint_text

    def test_enter_in_normal_mode_accepts(self):
        menu = self._make_menu(text="insp", input_active=False)
        assert tm._vim_search_key(menu, "enter") == "enter"
        assert menu._search.search_text == "insp"
        assert menu._search._vim_input_active is False

    def test_ctrl_u_clears_retained_filter(self):
        menu = self._make_menu(text="insp", input_active=False)
        assert tm._vim_search_key(menu, "ctrl-u") == ""
        assert menu._search.search_text is None
        assert menu._search._vim_input_active is False
        assert "Press" in menu._show_search_hint_text

    def test_raw_ctrl_u_clears_retained_filter(self):
        menu = self._make_menu(text="insp", input_active=False)
        assert tm._vim_search_key(menu, "\x15") == ""
        assert menu._search.search_text is None
        assert menu._search._vim_input_active is False

    def test_ctrl_u_without_filter_is_a_noop(self):
        menu = self._make_menu(input_active=False)
        assert tm._vim_search_key(menu, "ctrl-u") == ""
        assert menu._search.search_text is None

    def test_normal_mode_letter_passes_through(self):
        menu = self._make_menu(text="insp", input_active=False)
        assert tm._vim_search_key(menu, "j") == "j"

    def test_stale_input_flag_without_text_is_reset(self):
        menu = self._make_menu(input_active=True)
        assert tm._vim_search_key(menu, "escape") == "escape"
        assert menu._search._vim_input_active is False

    def test_hint_escapes_format_braces(self):
        menu = self._make_menu(text="{", input_active=True)
        assert tm._vim_search_key(menu, "j") == "j"
        assert "filter: {{" in menu._show_search_hint_text


class TestVimSearchReadNextKey:
    def _make_menu(self, text=None, input_active=False):
        menu = MagicMock()
        menu._terminal_code_to_codename = {"\x1b": "escape"}
        menu._tty_in = MagicMock()
        menu._tty_in.fileno.return_value = 0
        menu._reading_next_key = False
        menu._paint_before_next_read = False
        menu._paint_menu = MagicMock()
        menu._search_key = "/"
        menu._search = tm.TerminalMenu.Search(["about", "help"], search_text=text)
        _set_vim_input_active(menu._search, input_active)
        menu._vim_search_mode = True
        menu._show_search_hint_text = ""
        return menu

    def _call(self, menu, key_bytes, ignore_case=True):
        with patch("simple_term_menu.os.read", return_value=key_bytes):
            return tm.TerminalMenu._read_next_key(menu, ignore_case)

    def test_vim_mode_routes_slash(self):
        menu = self._make_menu()
        assert self._call(menu, b"/") == ""
        assert menu._search._vim_input_active is True

    def test_vim_mode_keeps_filter_on_escape(self):
        menu = self._make_menu(text="help", input_active=True)
        assert self._call(menu, b"\x1b") == ""
        assert menu._search.search_text == "help"
        assert menu._search._vim_input_active is False

    def test_vim_mode_keeps_filter_on_enter(self):
        menu = self._make_menu(text="help", input_active=True)
        menu._terminal_code_to_codename["\r"] = "enter"
        assert self._call(menu, b"\r") == ""
        assert menu._search.search_text == "help"
        assert menu._search._vim_input_active is False

    def test_non_vim_mode_passes_key_through(self):
        menu = self._make_menu()
        menu._vim_search_mode = False
        assert self._call(menu, b"x") == "x"


class TestThemeStylePatch:
    def test_patch_is_idempotent(self):
        tm._apply_theme_style_patch()

    def test_registers_style_names(self):
        for name in tm._THEME_STYLE_NAMES:
            assert name in tm.TerminalMenu._codename_to_capname

    def test_style_codes_use_theme_palette(self):
        from usecli.cli.config.colors import COLOR

        codes = tm._theme_style_codes()
        assert codes["usecli_primary"] == COLOR.ANSI.PRIMARY
        assert codes["usecli_secondary"] == COLOR.ANSI.SECONDARY
        assert codes["usecli_accent"] == COLOR.ANSI.ACCENT
        assert codes["usecli_muted"] == COLOR.ANSI.FOREGROUND_MUTED
        assert codes["usecli_foreground"] == COLOR.ANSI.FOREGROUND
        assert codes["usecli_dim"] == "\033[2m"
        assert codes["usecli_background"] == COLOR.ANSI.BACKGROUND
        assert codes["usecli_bg_primary"] == COLOR.ANSI.BG_PRIMARY
        assert codes["usecli_bg_secondary"] == COLOR.ANSI.BG_SECONDARY
        assert codes["usecli_bg_accent"] == COLOR.ANSI.BG_ACCENT

    def test_init_terminal_codes_injects_theme_styles(self):
        from usecli.cli.config.colors import COLOR

        original = tm.TerminalMenu._codename_to_terminal_code
        tm.TerminalMenu._codename_to_terminal_code = {"reset_attributes": ""}
        try:
            tm.TerminalMenu._init_terminal_codes()
            codes = tm.TerminalMenu._codename_to_terminal_code
            assert codes["usecli_primary"] == COLOR.ANSI.PRIMARY
            assert codes["usecli_bg_primary"] == COLOR.ANSI.BG_PRIMARY
        finally:
            tm.TerminalMenu._codename_to_terminal_code = original

    def test_patch_updates_already_initialized_codes(self):
        original_patch = tm._PATCHED_THEME_STYLES
        original_codes = tm.TerminalMenu._codename_to_terminal_code
        original_init = tm.TerminalMenu._init_terminal_codes
        try:
            tm._PATCHED_THEME_STYLES = False
            tm.TerminalMenu._codename_to_terminal_code = {"reset_attributes": ""}
            tm._apply_theme_style_patch()
            assert tm.TerminalMenu._codename_to_terminal_code["usecli_primary"]
        finally:
            tm._PATCHED_THEME_STYLES = original_patch
            tm.TerminalMenu._codename_to_terminal_code = original_codes
            init_attr = "_init_terminal_codes"
            setattr(tm.TerminalMenu, init_attr, original_init)


class TestAnsiWidthPatch:
    def test_patch_is_idempotent(self):
        tm._apply_ansi_width_patch()

    def test_width_ignores_ansi_sequences(self):
        assert tm.simple_term_menu.wcswidth("\x1b[38;2;1;2;3mabc\x1b[0m") == 3
        assert tm.simple_term_menu.wcswidth("abc") == 3


class TestColoredEntriesPatch:
    def test_patch_is_idempotent(self):
        tm._apply_colored_entries_patch()

    def _make_view(self):
        search = tm.TerminalMenu.Search(["one", "two"])
        viewport = MagicMock()
        viewport.lower_index = 0
        viewport.upper_index = 9
        return tm.TerminalMenu.View(["one", "two"], search, MagicMock(), viewport)

    def test_without_renderer_returns_plain_entries(self):
        view = self._make_view()
        assert [entry for _, _, entry in view] == ["one", "two"]

    def test_styles_inactive_entries_only(self):
        view = self._make_view()
        view._usecli_entry_renderer = lambda entry: f"<{entry}>"
        view.active_displayed_index = 0
        assert list(view) == [(0, 0, "one"), (1, 1, "<two>")]

    def test_searching_uses_plain_entries(self):
        view = self._make_view()
        view._usecli_entry_renderer = lambda entry: f"<{entry}>"
        view.active_displayed_index = 0
        view._search.search_text = "t"
        assert list(view) == [(0, 0, "one"), (1, 1, "two")]


class TestTitleAndEntryStyling:
    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_title_and_entry_renderer_are_applied(self, mock_menu_class):
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_instance._title_lines = ["Title"]
        mock_menu_instance._view = Mock()
        mock_menu_class.return_value = mock_menu_instance

        renderer = lambda entry: f"<{entry}>"
        terminal_menu(
            ["A"],
            title="Title",
            title_style="\033[36m",
            entry_renderer=renderer,
        )

        assert mock_menu_instance._title_lines == ["\033[36mTitle\033[0m"]
        assert mock_menu_instance._view._usecli_entry_renderer is renderer

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_title_style_ignores_non_line_titles(self, mock_menu_class):
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        terminal_menu(["A"], title="Title", title_style="\033[36m")

        assert isinstance(mock_menu_instance._title_lines, Mock)


class _FakeStream:
    """Minimal stand-in for a standard stream."""

    def __init__(self, tty=True):
        self._tty = tty
        self.closed = False
        self.flushes = 0
        self.written = []
        self.read_data = "x"

    def isatty(self):
        return self._tty

    def flush(self):
        self.flushes += 1

    def close(self):
        self.closed = True

    def read(self, size=-1):
        return self.read_data

    def write(self, text):
        self.written.append(text)
        return len(text)


class TestTtyFallbackPatch:
    def test_patch_is_idempotent(self):
        tm._apply_tty_fallback_patch()
        assert tm._PATCHED_TTY_FALLBACK is True
        assert getattr(tm.simple_term_menu, "open", None) is tm._open_tty_with_fallback

    @staticmethod
    def _fail_dev_tty_only(monkeypatch):
        original_open = tm.builtins.open

        def _open(file, mode="r", *args, **kwargs):
            if str(file) == "/dev/tty":
                raise OSError(6, "Device not configured", str(file))
            return original_open(file, mode, *args, **kwargs)

        monkeypatch.setattr(tm.builtins, "open", _open)

    def test_read_falls_back_to_stdin(self, monkeypatch):
        fake = _FakeStream()
        monkeypatch.setattr(tm.sys, "stdin", fake)
        self._fail_dev_tty_only(monkeypatch)

        stream = tm._open_tty_with_fallback("/dev/tty", "r", encoding="utf-8")
        assert stream.read() == "x"

        with stream as entered:
            assert entered is stream
        stream.close()
        assert fake.flushes == 2
        assert fake.closed is False

    def test_write_falls_back_to_stdout(self, monkeypatch):
        fake = _FakeStream()
        monkeypatch.setattr(tm.sys, "stdout", fake)
        self._fail_dev_tty_only(monkeypatch)

        stream = tm._open_tty_with_fallback(
            "/dev/tty", "w", encoding="utf-8", errors="replace"
        )
        stream.write("hi")
        stream.close()
        assert fake.written == ["hi"]
        assert fake.flushes == 1
        assert fake.closed is False

    def test_reraises_when_stdio_is_not_a_tty(self, monkeypatch):
        monkeypatch.setattr(tm.sys, "stdin", _FakeStream(tty=False))
        self._fail_dev_tty_only(monkeypatch)

        with pytest.raises(OSError, match="Device not configured"):
            tm._open_tty_with_fallback("/dev/tty", "r")

    def test_real_tty_open_is_used_when_available(self, monkeypatch):
        handle = object()
        real_open = tm.builtins.open

        def _open(file, mode="r", *args, **kwargs):
            if str(file) == "/dev/tty":
                return handle
            return real_open(file, mode, *args, **kwargs)

        monkeypatch.setattr(tm.builtins, "open", _open)

        assert tm._open_tty_with_fallback("/dev/tty", "r") is handle

    def test_other_paths_are_opened_directly(self):
        with tm._open_tty_with_fallback(__file__) as handle:
            assert "TestTtyFallbackPatch" in handle.read()
