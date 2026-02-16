"""Tests for error handling utility functions."""

from unittest.mock import patch

import pytest
import typer

from usecli.cli.config.colors import COLOR
from usecli.cli.core.error.utils import confirm_or_exit, error_exit


class TestErrorExit:
    """Test suite for error_exit function."""

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_with_message_only(self, mock_display_error):
        """Test error_exit with message only."""
        with pytest.raises(typer.Exit) as exc_info:
            error_exit("An error occurred")

        mock_display_error.assert_called_once_with("An error occurred", None)
        assert exc_info.value.exit_code == 1

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_with_message_and_suggestion(self, mock_display_error):
        """Test error_exit with message and suggestion."""
        with pytest.raises(typer.Exit) as exc_info:
            error_exit("An error occurred", suggestion="Try this fix")

        mock_display_error.assert_called_once_with("An error occurred", "Try this fix")
        assert exc_info.value.exit_code == 1

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_with_custom_code(self, mock_display_error):
        """Test error_exit with custom exit code."""
        with pytest.raises(typer.Exit) as exc_info:
            error_exit("Error", code=42)

        assert exc_info.value.exit_code == 42

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_with_all_parameters(self, mock_display_error):
        """Test error_exit with message, suggestion, and code."""
        with pytest.raises(typer.Exit) as exc_info:
            error_exit("Error message", suggestion="Fix this", code=99)

        mock_display_error.assert_called_once_with("Error message", "Fix this")
        assert exc_info.value.exit_code == 99

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_default_code_is_one(self, mock_display_error):
        """Test error_exit defaults to exit code 1."""
        with pytest.raises(typer.Exit) as exc_info:
            error_exit("Error")

        assert exc_info.value.exit_code == 1

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_none_suggestion(self, mock_display_error):
        """Test error_exit with None suggestion."""
        with pytest.raises(typer.Exit):
            error_exit("Error", suggestion=None)

        mock_display_error.assert_called_once_with("Error", None)

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_empty_suggestion(self, mock_display_error):
        """Test error_exit with empty string suggestion."""
        with pytest.raises(typer.Exit):
            error_exit("Error", suggestion="")

        mock_display_error.assert_called_once_with("Error", "")

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_long_message(self, mock_display_error):
        """Test error_exit with long message."""
        long_message = "A" * 500
        with pytest.raises(typer.Exit):
            error_exit(long_message)

        mock_display_error.assert_called_once()

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_special_characters(self, mock_display_error):
        """Test error_exit handles special characters."""
        message = "Error: [brackets] and {braces}"
        with pytest.raises(typer.Exit):
            error_exit(message)

        mock_display_error.assert_called_once()

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_zero_code(self, mock_display_error):
        """Test error_exit with exit code 0."""
        with pytest.raises(typer.Exit) as exc_info:
            error_exit("Message", code=0)

        assert exc_info.value.exit_code == 0

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_calls_display_error(self, mock_display_error):
        """Test error_exit calls ErrorHandler.display_error."""
        with pytest.raises(typer.Exit):
            error_exit("Test", "Suggestion")

        assert mock_display_error.called

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_raises_typer_exit(self, mock_display_error):
        """Test error_exit raises typer.Exit."""
        with pytest.raises(typer.Exit):
            error_exit("Error")

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_negative_code(self, mock_display_error):
        """Test error_exit with negative exit code."""
        with pytest.raises(typer.Exit) as exc_info:
            error_exit("Error", code=-1)

        assert exc_info.value.exit_code == -1

    @patch("usecli.cli.core.error.utils.ErrorHandler.display_error")
    def test_error_exit_multiple_calls(self, mock_display_error):
        """Test multiple error_exit calls are independent."""
        with pytest.raises(typer.Exit):
            error_exit("First error", code=1)

        with pytest.raises(typer.Exit):
            error_exit("Second error", code=2)

        assert mock_display_error.call_count == 2


class TestConfirmOrExit:
    """Test suite for confirm_or_exit function."""

    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_user_confirms(self, mock_confirm):
        """Test confirm_or_exit returns True when user confirms."""
        mock_confirm.return_value = True

        result = confirm_or_exit("Continue?")

        assert result is True
        mock_confirm.assert_called_once()

    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_user_cancels(self, mock_confirm):
        """Test confirm_or_exit raises Exit when user cancels."""
        mock_confirm.return_value = False

        with pytest.raises(typer.Exit) as exc_info:
            confirm_or_exit("Continue?")

        assert exc_info.value.exit_code == 130

    @patch("usecli.cli.core.error.utils.console")
    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_displays_exit_message(self, mock_confirm, mock_console):
        """Test confirm_or_exit displays exit message when cancelled."""
        mock_confirm.return_value = False

        with pytest.raises(typer.Exit):
            confirm_or_exit("Continue?", exit_message="Goodbye")

        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Goodbye" in call_args

    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_default_exit_message(self, mock_confirm):
        """Test confirm_or_exit uses default exit message."""
        mock_confirm.return_value = False

        with pytest.raises(typer.Exit):
            confirm_or_exit("Continue?")

        # Default message should be "Operation cancelled"
        mock_confirm.assert_called_once()

    @patch("usecli.cli.core.error.utils.console")
    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_custom_exit_message(self, mock_confirm, mock_console):
        """Test confirm_or_exit with custom exit message."""
        mock_confirm.return_value = False
        custom_message = "Custom exit message"

        with pytest.raises(typer.Exit):
            confirm_or_exit("Continue?", exit_message=custom_message)

        call_args = mock_console.print.call_args[0][0]
        assert custom_message in call_args

    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_confirm_message_styled(self, mock_confirm):
        """Test confirm_or_exit passes styled message to Confirm.ask."""
        mock_confirm.return_value = True
        message = "Continue?"

        confirm_or_exit(message)

        call_args = mock_confirm.call_args[0][0]
        assert message in call_args
        assert f"[bold {COLOR.SECONDARY}]" in call_args

    @patch("usecli.cli.core.error.utils.console")
    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_exit_message_styled(self, mock_confirm, mock_console):
        """Test confirm_or_exit exit message is styled."""
        mock_confirm.return_value = False

        with pytest.raises(typer.Exit):
            confirm_or_exit("Continue?", exit_message="Cancelled")

        call_args = mock_console.print.call_args[0][0]
        assert COLOR.WARNING in call_args

    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_exit_code_is_130(self, mock_confirm):
        """Test confirm_or_exit uses exit code 130 (Ctrl+C standard)."""
        mock_confirm.return_value = False

        with pytest.raises(typer.Exit) as exc_info:
            confirm_or_exit("Continue?")

        assert exc_info.value.exit_code == 130

    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_does_not_print_on_confirm(self, mock_confirm):
        """Test confirm_or_exit doesn't print exit message on confirm."""
        mock_confirm.return_value = True

        with patch("usecli.cli.core.error.utils.console") as mock_console:
            result = confirm_or_exit("Continue?")

            # console.print should not be called
            mock_console.print.assert_not_called()
            assert result is True

    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_long_message(self, mock_confirm):
        """Test confirm_or_exit with long message."""
        mock_confirm.return_value = True
        long_message = "A" * 500

        result = confirm_or_exit(long_message)

        assert result is True
        call_args = mock_confirm.call_args[0][0]
        assert "A" * 500 in call_args

    @patch("usecli.cli.core.error.utils.console")
    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_empty_exit_message(self, mock_confirm, mock_console):
        """Test confirm_or_exit with empty exit message."""
        mock_confirm.return_value = False

        with pytest.raises(typer.Exit):
            confirm_or_exit("Continue?", exit_message="")

        mock_console.print.assert_called_once()

    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_multiple_calls_independent(self, mock_confirm):
        """Test multiple confirm_or_exit calls are independent."""
        # First call: user confirms
        mock_confirm.return_value = True
        result1 = confirm_or_exit("First prompt?")
        assert result1 is True

        # Second call: user cancels
        mock_confirm.return_value = False
        with pytest.raises(typer.Exit) as exc_info:
            confirm_or_exit("Second prompt?")
        assert exc_info.value.exit_code == 130

    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_special_characters_in_message(self, mock_confirm):
        """Test confirm_or_exit handles special characters in message."""
        mock_confirm.return_value = True
        message = "Continue? [y/n]"

        result = confirm_or_exit(message)

        assert result is True
        call_args = mock_confirm.call_args[0][0]
        assert "[y/n]" in call_args

    @patch("usecli.cli.core.error.utils.console")
    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_special_characters_in_exit_message(
        self, mock_confirm, mock_console
    ):
        """Test confirm_or_exit handles special characters in exit message."""
        mock_confirm.return_value = False
        exit_message = "Exiting [cancelled]"

        with pytest.raises(typer.Exit):
            confirm_or_exit("Continue?", exit_message=exit_message)

        call_args = mock_console.print.call_args[0][0]
        assert exit_message in call_args

    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_returns_only_true(self, mock_confirm):
        """Test confirm_or_exit returns True (not just truthy)."""
        mock_confirm.return_value = True

        result = confirm_or_exit("Continue?")

        assert result is True
        assert type(result) is bool

    @patch("usecli.cli.core.error.utils.console")
    @patch("usecli.cli.core.error.utils.Confirm.ask")
    def test_confirm_or_exit_prints_once_on_cancel(self, mock_confirm, mock_console):
        """Test confirm_or_exit prints exactly once on cancel."""
        mock_confirm.return_value = False

        with pytest.raises(typer.Exit):
            confirm_or_exit("Continue?")

        # console.print should be called exactly once for exit message
        assert mock_console.print.call_count == 1
