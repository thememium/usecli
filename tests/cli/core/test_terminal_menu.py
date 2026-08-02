"""Comprehensive tests for terminal_menu function."""

import os
from unittest.mock import Mock, patch

# Import the function to test
from usecli.cli.utils.interactive.terminal_menu import terminal_menu


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

        assert call_kwargs["menu_cursor_style"] == ("fg_cyan", "bold")
        assert call_kwargs["menu_highlight_style"] == ("bg_cyan", "fg_black")
        assert call_kwargs["status_bar_style"] == ("fg_cyan", "bold")
        assert call_kwargs["multi_select_cursor_style"] == ("fg_cyan", "bold")

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
