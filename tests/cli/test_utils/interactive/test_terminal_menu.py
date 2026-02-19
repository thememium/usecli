"""Comprehensive tests for terminal_menu function."""

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
        # Setup
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 1
        mock_menu_class.return_value = mock_menu_instance

        options = ["Option A", "Option B", "Option C"]

        # Execute
        result = terminal_menu(options)

        # Assert
        assert result == ["Option B"]
        assert len(result) == 1
        mock_menu_instance.show.assert_called_once()

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_select_first_option(self, mock_menu_class):
        """Test selecting first option returns first item."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        options = ["First", "Second", "Third"]

        result = terminal_menu(options)

        assert result == ["First"]

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_select_last_option(self, mock_menu_class):
        """Test selecting last option returns last item."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 2
        mock_menu_class.return_value = mock_menu_instance

        options = ["First", "Second", "Third"]

        result = terminal_menu(options)

        assert result == ["Third"]

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_select_cancel_returns_empty_list(self, mock_menu_class):
        """Test that pressing cancel (None) returns empty list."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = None
        mock_menu_class.return_value = mock_menu_instance

        options = ["Option A", "Option B"]

        result = terminal_menu(options)

        assert result == []

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_select_with_title(self, mock_menu_class):
        """Test that title is passed to TerminalMenu."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        options = ["Option 1", "Option 2"]
        title = "Select your choice"

        result = terminal_menu(options, title=title)

        assert result == ["Option 1"]
        # Verify title was passed to TerminalMenu
        call_kwargs = mock_menu_class.call_args.kwargs
        assert call_kwargs.get("title") == title

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_select_with_non_string_options(self, mock_menu_class):
        """Test single select with integer options."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 1
        mock_menu_class.return_value = mock_menu_instance

        options = [10, 20, 30]

        result = terminal_menu(options)

        assert result == [20]
        # Verify display options were stringified
        call_args = mock_menu_class.call_args[0][0]
        assert call_args == ["10", "20", "30"]

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_select_with_tuple_result_returns_empty(self, mock_menu_class):
        """Test single select mode with tuple result (should be handled for multi_select)."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = (0, 1)
        mock_menu_class.return_value = mock_menu_instance

        options = ["Option A", "Option B", "Option C"]

        # In single select mode, tuple result is not expected but should return empty
        result = terminal_menu(options, multi_select=False)

        assert result == []


class TestTerminalMenuMultiSelectMode:
    """Test cases for terminal_menu in multi-select mode."""

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_with_single_int_result(self, mock_menu_class):
        """Test multi select when menu.show() returns single int."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 1
        mock_menu_class.return_value = mock_menu_instance

        options = ["Option A", "Option B", "Option C"]

        result = terminal_menu(options, multi_select=True)

        assert result == ["Option B"]
        assert len(result) == 1

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_with_tuple_result(self, mock_menu_class):
        """Test multi select when menu.show() returns tuple of indices."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = (0, 2)
        mock_menu_class.return_value = mock_menu_instance

        options = ["Option A", "Option B", "Option C"]

        result = terminal_menu(options, multi_select=True)

        assert result == ["Option A", "Option C"]
        assert len(result) == 2

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_with_multiple_items(self, mock_menu_class):
        """Test multi select with three items selected."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = (0, 1, 2)
        mock_menu_class.return_value = mock_menu_instance

        options = ["First", "Second", "Third"]

        result = terminal_menu(options, multi_select=True)

        assert result == ["First", "Second", "Third"]
        assert len(result) == 3

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_cancel_returns_empty_list(self, mock_menu_class):
        """Test that canceling multi select returns empty list."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = None
        mock_menu_class.return_value = mock_menu_instance

        options = ["Option A", "Option B", "Option C"]

        result = terminal_menu(options, multi_select=True)

        assert result == []

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_no_selection_returns_empty_list(self, mock_menu_class):
        """Test multi select with empty tuple (no selections) returns empty list."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = ()
        mock_menu_class.return_value = mock_menu_instance

        options = ["Option A", "Option B"]

        result = terminal_menu(options, multi_select=True)

        assert result == []

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_with_title(self, mock_menu_class):
        """Test that multi_select_hint is shown when multi_select=True."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = (0, 1)
        mock_menu_class.return_value = mock_menu_instance

        options = ["A", "B", "C"]
        title = "Select multiple items"

        result = terminal_menu(options, title=title, multi_select=True)

        assert result == ["A", "B"]
        # Verify multi_select parameters were set
        call_kwargs = mock_menu_class.call_args.kwargs
        assert call_kwargs.get("multi_select") is True
        assert call_kwargs.get("show_multi_select_hint") is True

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_multi_select_invalid_return_type(self, mock_menu_class):
        """Test multi select with invalid return type (string) returns empty."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = "invalid"
        mock_menu_class.return_value = mock_menu_instance

        options = ["Option A", "Option B"]

        result = terminal_menu(options, multi_select=True)

        assert result == []


class TestTerminalMenuMenuConfiguration:
    """Test cases for TerminalMenu configuration."""

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_menu_styling_configuration(self, mock_menu_class):
        """Test that all styling parameters are passed to TerminalMenu."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        options = ["A", "B"]
        terminal_menu(options)

        call_kwargs = mock_menu_class.call_args.kwargs

        # Verify all styling parameters
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

        options = ["A", "B"]
        terminal_menu(options, multi_select=True)

        call_kwargs = mock_menu_class.call_args.kwargs

        assert call_kwargs["multi_select_select_on_accept"] is False
        assert call_kwargs["multi_select_empty_ok"] is True

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_display_options_are_strings(self, mock_menu_class):
        """Test that display options are converted to strings."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        options = [1, 2, 3]
        terminal_menu(options)

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

        options = ["Option A", "Option B"]
        status_bar = "Enter = select • Esc = quit"

        terminal_menu(
            options,
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


class TestTerminalMenuWithCustomTypes:
    """Test cases with custom object types."""

    def test_with_integer_options(self):
        """Test with integer options."""

        @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
        def run_test(mock_menu_class):
            mock_menu_instance = Mock()
            mock_menu_instance.show.return_value = 1
            mock_menu_class.return_value = mock_menu_instance

            options = [100, 200, 300]
            result = terminal_menu(options)

            assert result == [200]

        run_test()

    def test_with_float_options(self):
        """Test with float options."""

        @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
        def run_test(mock_menu_class):
            mock_menu_instance = Mock()
            mock_menu_instance.show.return_value = 0
            mock_menu_class.return_value = mock_menu_instance

            options = [1.5, 2.5, 3.5]
            result = terminal_menu(options)

            assert result == [1.5]

        run_test()

    def test_with_custom_objects(self):
        """Test with custom objects that have __str__ method."""

        class Item:
            def __init__(self, name: str, value: int):
                self.name = name
                self.value = value

            def __str__(self):
                return f"{self.name} ({self.value})"

        @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
        def run_test(mock_menu_class):
            mock_menu_instance = Mock()
            mock_menu_instance.show.return_value = 1
            mock_menu_class.return_value = mock_menu_instance

            item1 = Item("Item 1", 10)
            item2 = Item("Item 2", 20)
            item3 = Item("Item 3", 30)

            options = [item1, item2, item3]
            result = terminal_menu(options)

            assert result == [item2]
            assert result[0].value == 20

            # Verify display options
            display_options = mock_menu_class.call_args[0][0]
            assert display_options == ["Item 1 (10)", "Item 2 (20)", "Item 3 (30)"]

        run_test()

    def test_with_mixed_types(self):
        """Test with mixed types."""

        @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
        def run_test(mock_menu_class):
            mock_menu_instance = Mock()
            mock_menu_instance.show.return_value = 1
            mock_menu_class.return_value = mock_menu_instance

            options = ["string", 42, 3.14]
            result = terminal_menu(options)

            assert result == [42]

            # Verify display is stringified
            display_options = mock_menu_class.call_args[0][0]
            assert display_options == ["string", "42", "3.14"]

        run_test()


class TestTerminalMenuEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_single_option_list(self, mock_menu_class):
        """Test with only one option."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        options = ["Only Option"]
        result = terminal_menu(options)

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

        options = ["Option 🎯", "Option ✓", "Option ✗"]
        result = terminal_menu(options)

        assert result == ["Option ✓"]

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_options_with_empty_strings(self, mock_menu_class):
        """Test options including empty strings."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 0
        mock_menu_class.return_value = mock_menu_instance

        options = ["", "Non-empty", ""]
        result = terminal_menu(options)

        assert result == [""]

    @patch("usecli.cli.utils.interactive.terminal_menu.TerminalMenu")
    def test_options_with_whitespace(self, mock_menu_class):
        """Test options with various whitespace."""
        mock_menu_instance = Mock()
        mock_menu_instance.show.return_value = 1
        mock_menu_class.return_value = mock_menu_instance

        options = ["  spaces  ", "\ttabs\t", "\nnewline\n"]
        result = terminal_menu(options)

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
        options = [obj]
        result = terminal_menu(options)

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

        options = ["Choice 1", "Choice 2", "Choice 3"]
        result = terminal_menu(options, title="Select an option", multi_select=False)

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

        options = ["Option A", "Option B", "Option C"]
        result = terminal_menu(
            options, title="Select multiple options", multi_select=True
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

        options1 = ["A", "B"]
        options2 = [1, 2, 3]

        result1 = terminal_menu(options1)
        result2 = terminal_menu(options2, multi_select=True)

        assert result1 == ["A"]
        assert result2 == [2]
        assert mock_menu_class.call_count == 2
