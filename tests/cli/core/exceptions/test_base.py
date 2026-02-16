"""Tests for UsecliError base exception class."""

from unittest.mock import MagicMock, patch

from usecli.cli.config.colors import COLOR
from usecli.cli.core.exceptions.base import UsecliError


class TestUsecliError:
    """Test suite for UsecliError class."""

    def test_initialization_with_message_only(self):
        """Test UsecliError initialization with message only."""
        message = "Something went wrong"
        error = UsecliError(message)

        assert error.message == message
        assert error.suggestion is None
        assert error.exit_code == 1

    def test_initialization_with_message_and_suggestion(self):
        """Test UsecliError initialization with message and suggestion."""
        message = "Something went wrong"
        suggestion = "Try running 'usecli init'"
        error = UsecliError(message, suggestion)

        assert error.message == message
        assert error.suggestion == suggestion
        assert error.exit_code == 1

    def test_exit_code_value(self):
        """Test UsecliError exit_code is 1."""
        error = UsecliError("Test error")
        assert error.exit_code == 1

    @patch("usecli.cli.core.exceptions.base.console")
    def test_show_without_suggestion(self, mock_console):
        """Test show() method without suggestion."""
        message = "An error occurred"
        error = UsecliError(message)
        error.show()

        # Verify console.print was called exactly once
        assert mock_console.print.call_count == 1

        # Verify the message contains the error icon and styled message
        call_args = mock_console.print.call_args[0][0]
        assert "✗" in call_args
        assert "An error occurred" in call_args
        assert COLOR.ERROR in call_args

    @patch("usecli.cli.core.exceptions.base.console")
    def test_show_with_suggestion(self, mock_console):
        """Test show() method with suggestion."""
        message = "An error occurred"
        suggestion = "Please check the logs"
        error = UsecliError(message, suggestion)
        error.show()

        # Verify console.print was called twice
        assert mock_console.print.call_count == 2

        # Verify first call contains error message
        first_call = mock_console.print.call_args_list[0][0][0]
        assert "✗" in first_call
        assert "An error occurred" in first_call

        # Verify second call contains suggestion
        second_call = mock_console.print.call_args_list[1][0][0]
        assert "💡" in second_call
        assert "Please check the logs" in second_call
        assert COLOR.WARNING in second_call

    @patch("usecli.cli.core.exceptions.base.console")
    def test_show_styling_correct(self, mock_console):
        """Test show() method applies correct styling."""
        message = "Error message"
        suggestion = "Suggestion"
        error = UsecliError(message, suggestion)
        error.show()

        # Check first call (error message)
        error_call = mock_console.print.call_args_list[0][0][0]
        assert f"[bold {COLOR.ERROR}]" in error_call
        assert f"[/bold {COLOR.ERROR}]" in error_call

        # Check second call (suggestion)
        suggestion_call = mock_console.print.call_args_list[1][0][0]
        assert f"[dim {COLOR.WARNING}]" in suggestion_call
        assert f"[/dim {COLOR.WARNING}]" in suggestion_call

    @patch("usecli.cli.core.exceptions.base.console")
    def test_show_with_file_parameter(self, mock_console):
        """Test show() method accepts file parameter."""
        error = UsecliError("Test error")
        file_obj = MagicMock()

        # Should not raise an exception
        error.show(file=file_obj)

        # Verify console.print was still called
        assert mock_console.print.called

    def test_inherits_from_click_exception(self):
        """Test UsecliError inherits from ClickException."""
        from click.exceptions import ClickException

        error = UsecliError("Test")
        assert isinstance(error, ClickException)

    def test_suggestion_is_optional(self):
        """Test suggestion parameter is truly optional."""
        error1 = UsecliError("Message")
        error2 = UsecliError("Message", None)

        assert error1.suggestion is None
        assert error2.suggestion is None

    @patch("usecli.cli.core.exceptions.base.console")
    def test_show_empty_message(self, mock_console):
        """Test show() with empty message."""
        error = UsecliError("")
        error.show()

        assert mock_console.print.called

    @patch("usecli.cli.core.exceptions.base.console")
    def test_show_long_message(self, mock_console):
        """Test show() with long message."""
        long_message = "A" * 500
        error = UsecliError(long_message)
        error.show()

        call_args = mock_console.print.call_args[0][0]
        assert "A" * 500 in call_args

    @patch("usecli.cli.core.exceptions.base.console")
    def test_show_special_characters_in_message(self, mock_console):
        """Test show() handles special characters in message."""
        message = "Error: [brackets] and {braces} and <tags>"
        error = UsecliError(message)
        error.show()

        call_args = mock_console.print.call_args[0][0]
        assert "Error:" in call_args

    @patch("usecli.cli.core.exceptions.base.console")
    def test_show_unicode_characters(self, mock_console):
        """Test show() handles unicode characters."""
        message = "Error with émojis 🚀 and spëcial chars"
        error = UsecliError(message)
        error.show()

        call_args = mock_console.print.call_args[0][0]
        assert "Error" in call_args

    def test_multiple_instances_independent(self):
        """Test multiple UsecliError instances are independent."""
        error1 = UsecliError("Error 1", "Suggestion 1")
        error2 = UsecliError("Error 2", "Suggestion 2")

        assert error1.message == "Error 1"
        assert error1.suggestion == "Suggestion 1"
        assert error2.message == "Error 2"
        assert error2.suggestion == "Suggestion 2"

    @patch("usecli.cli.core.exceptions.base.console")
    def test_show_icon_is_correct(self, mock_console):
        """Test show() uses correct error icon (✗)."""
        error = UsecliError("Test")
        error.show()

        call_args = mock_console.print.call_args[0][0]
        assert "✗" in call_args

    @patch("usecli.cli.core.exceptions.base.console")
    def test_show_suggestion_icon_is_correct(self, mock_console):
        """Test show() uses correct suggestion icon (💡)."""
        error = UsecliError("Test", "Suggestion")
        error.show()

        suggestion_call = mock_console.print.call_args_list[1][0][0]
        assert "💡" in suggestion_call
