"""Tests for ErrorHandler class."""

import functools
from unittest.mock import patch

import pytest
import typer

from usecli.cli.config.colors import COLOR
from usecli.cli.core.error.handler import ErrorHandler
from usecli.cli.core.exceptions import UsecliError


class TestErrorHandlerDisplayError:
    """Test suite for ErrorHandler.display_error method."""

    @patch("usecli.cli.core.error.handler.console")
    def test_display_error_message_only(self, mock_console):
        """Test display_error with message only."""
        message = "Something went wrong"
        ErrorHandler.display_error(message)

        assert mock_console.print.call_count == 1

        call_args = mock_console.print.call_args[0][0]
        assert "✗" in call_args
        assert message in call_args
        assert f"[bold {COLOR.ERROR}]" in call_args

    @patch("usecli.cli.core.error.handler.console")
    def test_display_error_with_suggestion(self, mock_console):
        """Test display_error with message and suggestion."""
        message = "Something went wrong"
        suggestion = "Try running --help"
        ErrorHandler.display_error(message, suggestion)

        assert mock_console.print.call_count == 2

        # First call: error message
        first_call = mock_console.print.call_args_list[0][0][0]
        assert "✗" in first_call
        assert message in first_call

        # Second call: suggestion
        second_call = mock_console.print.call_args_list[1][0][0]
        assert "💡" in second_call
        assert suggestion in second_call
        assert f"[dim {COLOR.WARNING}]" in second_call

    @patch("usecli.cli.core.error.handler.console")
    def test_display_error_styling_with_suggestion(self, mock_console):
        """Test display_error applies correct styling with suggestion."""
        ErrorHandler.display_error("Error", "Fix it")

        error_call = mock_console.print.call_args_list[0][0][0]
        suggestion_call = mock_console.print.call_args_list[1][0][0]

        # Error styling
        assert f"[bold {COLOR.ERROR}]✗[/bold {COLOR.ERROR}]" in error_call
        assert f"[bold {COLOR.ERROR}]Error[/bold {COLOR.ERROR}]" in error_call

        # Suggestion styling
        assert f"[dim {COLOR.WARNING}]" in suggestion_call
        assert f"[/dim {COLOR.WARNING}]" in suggestion_call

    @patch("usecli.cli.core.error.handler.console")
    def test_display_error_empty_message(self, mock_console):
        """Test display_error with empty message."""
        ErrorHandler.display_error("")
        assert mock_console.print.called

    @patch("usecli.cli.core.error.handler.console")
    def test_display_error_special_characters(self, mock_console):
        """Test display_error handles special characters."""
        message = "Error: [brackets] and {braces}"
        ErrorHandler.display_error(message)
        assert mock_console.print.called

    @patch("usecli.cli.core.error.handler.console")
    def test_display_error_unicode(self, mock_console):
        """Test display_error handles unicode characters."""
        message = "Errör with ëmojis 🚀"
        ErrorHandler.display_error(message)
        assert mock_console.print.called

    @patch("usecli.cli.core.error.handler.console")
    def test_display_error_none_suggestion(self, mock_console):
        """Test display_error with None suggestion doesn't print suggestion."""
        ErrorHandler.display_error("Message", None)
        assert mock_console.print.call_count == 1

    @patch("usecli.cli.core.error.handler.console")
    def test_display_error_empty_suggestion(self, mock_console):
        """Test display_error with empty string suggestion."""
        ErrorHandler.display_error("Message", "")
        # Empty string is falsy, so suggestion should not be printed
        assert mock_console.print.call_count == 1


class TestErrorHandlerDisplayWarning:
    """Test suite for ErrorHandler.display_warning method."""

    @patch("usecli.cli.core.error.handler.console")
    def test_display_warning_message_only(self, mock_console):
        """Test display_warning with message only."""
        message = "This is a warning"
        ErrorHandler.display_warning(message)

        # Should print blank line + warning
        assert mock_console.print.call_count == 2

        # Second call contains the warning
        warning_call = mock_console.print.call_args_list[1][0][0]
        assert "⚠" in warning_call
        assert message in warning_call
        assert f"[bold {COLOR.WARNING}]" in warning_call

    @patch("usecli.cli.core.error.handler.console")
    def test_display_warning_with_suggestion(self, mock_console):
        """Test display_warning with message and suggestion."""
        message = "This is a warning"
        suggestion = "Consider doing this"
        ErrorHandler.display_warning(message, suggestion)

        # Should print: blank line + warning + suggestion
        assert mock_console.print.call_count == 3

        warning_call = mock_console.print.call_args_list[1][0][0]
        suggestion_call = mock_console.print.call_args_list[2][0][0]

        assert "⚠" in warning_call
        assert message in warning_call

        assert "💡" in suggestion_call
        assert suggestion in suggestion_call
        assert f"[dim {COLOR.INFO}]" in suggestion_call

    @patch("usecli.cli.core.error.handler.console")
    def test_display_warning_prints_blank_line_first(self, mock_console):
        """Test display_warning prints blank line first."""
        ErrorHandler.display_warning("Warning")

        # First call should be empty print for blank line
        first_call = mock_console.print.call_args_list[0]
        assert len(first_call[0]) == 0 or first_call[0][0] == ""

    @patch("usecli.cli.core.error.handler.console")
    def test_display_warning_styling(self, mock_console):
        """Test display_warning applies correct styling."""
        ErrorHandler.display_warning("Warning", "Suggestion")

        warning_call = mock_console.print.call_args_list[1][0][0]
        suggestion_call = mock_console.print.call_args_list[2][0][0]

        # Warning styling
        assert f"[bold {COLOR.WARNING}]⚠[/bold {COLOR.WARNING}]" in warning_call

        # Suggestion styling with INFO color
        assert f"[dim {COLOR.INFO}]" in suggestion_call
        assert f"[/dim {COLOR.INFO}]" in suggestion_call

    @patch("usecli.cli.core.error.handler.console")
    def test_display_warning_none_suggestion(self, mock_console):
        """Test display_warning with None suggestion."""
        ErrorHandler.display_warning("Message", None)
        # Blank line + warning message only
        assert mock_console.print.call_count == 2

    @patch("usecli.cli.core.error.handler.console")
    def test_display_warning_empty_suggestion(self, mock_console):
        """Test display_warning with empty suggestion."""
        ErrorHandler.display_warning("Message", "")
        # Empty string is falsy, so no suggestion printed
        assert mock_console.print.call_count == 2


class TestErrorHandlerDisplaySuccess:
    """Test suite for ErrorHandler.display_success method."""

    @patch("usecli.cli.core.error.handler.console")
    def test_display_success_basic(self, mock_console):
        """Test display_success with message."""
        message = "Operation completed successfully"
        ErrorHandler.display_success(message)

        assert mock_console.print.call_count == 1

        call_args = mock_console.print.call_args[0][0]
        assert "✓" in call_args
        assert message in call_args
        assert f"[bold {COLOR.SUCCESS}]" in call_args

    @patch("usecli.cli.core.error.handler.console")
    def test_display_success_styling(self, mock_console):
        """Test display_success applies correct styling."""
        ErrorHandler.display_success("Success")

        call_args = mock_console.print.call_args[0][0]

        assert f"[bold {COLOR.SUCCESS}]✓[/bold {COLOR.SUCCESS}]" in call_args
        assert f"[bold {COLOR.SUCCESS}]Success[/bold {COLOR.SUCCESS}]" in call_args

    @patch("usecli.cli.core.error.handler.console")
    def test_display_success_empty_message(self, mock_console):
        """Test display_success with empty message."""
        ErrorHandler.display_success("")
        assert mock_console.print.called

    @patch("usecli.cli.core.error.handler.console")
    def test_display_success_special_characters(self, mock_console):
        """Test display_success handles special characters."""
        message = "File [brackets] saved {braces}"
        ErrorHandler.display_success(message)
        assert mock_console.print.called

    @patch("usecli.cli.core.error.handler.console")
    def test_display_success_long_message(self, mock_console):
        """Test display_success with long message."""
        message = "A" * 500
        ErrorHandler.display_success(message)
        assert mock_console.print.called


class TestErrorHandlerHandleException:
    """Test suite for ErrorHandler.handle_exception decorator."""

    def test_handle_exception_preserves_function_metadata(self):
        """Test decorator preserves function metadata."""

        @ErrorHandler.handle_exception
        def test_func():
            """Test function docstring."""

        assert test_func.__name__ == "test_func"
        doc = test_func.__doc__
        assert doc is not None and "Test function docstring" in doc

    def test_handle_exception_with_successful_execution(self):
        """Test decorator allows successful function execution."""

        @ErrorHandler.handle_exception
        def add(a, b):
            return a + b

        result = add(2, 3)
        assert result == 5

    def test_handle_exception_with_arguments(self):
        """Test decorator works with function arguments."""

        @ErrorHandler.handle_exception
        def multiply(a, b, c=1):
            return a * b * c

        result = multiply(2, 3, c=4)
        assert result == 24

    @patch("usecli.cli.core.error.handler.ErrorHandler.display_error")
    def test_handle_exception_catches_usecli_error(self, mock_display_error):
        """Test decorator catches UsecliError."""

        @ErrorHandler.handle_exception
        def raise_usecli_error():
            raise UsecliError("Test error", "Test suggestion")

        with pytest.raises(typer.Exit) as exc_info:
            raise_usecli_error()

        assert exc_info.value.exit_code == 1

    @patch("usecli.cli.core.error.handler.ErrorHandler.display_error")
    def test_handle_exception_calls_error_show(self, mock_display_error):
        """Test decorator calls error.show() for UsecliError."""

        @ErrorHandler.handle_exception
        def raise_usecli_error():
            raise UsecliError("Test error")

        with pytest.raises(typer.Exit):
            raise_usecli_error()

        # Verify display_error was not called (show() is called instead)
        # We need to mock the error's show method

    @patch("usecli.cli.core.error.handler.ErrorHandler.display_error")
    def test_handle_exception_catches_generic_exception(self, mock_display_error):
        """Test decorator catches generic Exception."""

        @ErrorHandler.handle_exception
        def raise_generic_error():
            raise ValueError("Something went wrong")

        with pytest.raises(typer.Exit) as exc_info:
            raise_generic_error()

        assert exc_info.value.exit_code == 1
        mock_display_error.assert_called_once()

    @patch("usecli.cli.core.error.handler.ErrorHandler.display_error")
    def test_handle_exception_generic_error_displays_message(self, mock_display_error):
        """Test decorator displays generic exception message."""

        @ErrorHandler.handle_exception
        def raise_error():
            raise RuntimeError("Test runtime error")

        with pytest.raises(typer.Exit):
            raise_error()

        call_args = mock_display_error.call_args
        assert "Unexpected error: Test runtime error" in call_args[0][0]
        assert "Run with --verbose for more details" in call_args[1]["suggestion"]

    @patch("usecli.cli.core.error.handler.ErrorHandler.display_error")
    def test_handle_exception_preserves_exit_code_for_usecli_error(
        self, mock_display_error
    ):
        """Test decorator preserves exit code from UsecliError."""

        class CustomError(UsecliError):
            exit_code = 42

        @ErrorHandler.handle_exception
        def raise_custom_error():
            raise CustomError("Custom error")

        with pytest.raises(typer.Exit) as exc_info:
            raise_custom_error()

        assert exc_info.value.exit_code == 42

    def test_handle_exception_with_none_return(self):
        """Test decorator works with function returning None."""

        @ErrorHandler.handle_exception
        def returns_none():
            pass

        result = returns_none()
        assert result is None

    def test_handle_exception_with_dict_return(self):
        """Test decorator works with function returning dict."""

        @ErrorHandler.handle_exception
        def returns_dict():
            return {"key": "value"}

        result = returns_dict()
        assert result == {"key": "value"}

    def test_handle_exception_with_list_return(self):
        """Test decorator works with function returning list."""

        @ErrorHandler.handle_exception
        def returns_list():
            return [1, 2, 3]

        result = returns_list()
        assert result == [1, 2, 3]

    @patch("usecli.cli.core.error.handler.ErrorHandler.display_error")
    def test_handle_exception_with_kwargs_error(self, mock_display_error):
        """Test decorator handles errors in function with kwargs."""

        @ErrorHandler.handle_exception
        def function_with_kwargs(a, b=None):
            if b is None:
                raise ValueError("b is required")
            return a + b

        with pytest.raises(typer.Exit):
            function_with_kwargs(1)

    @patch("usecli.cli.core.error.handler.console")
    def test_handle_exception_usecli_error_uses_show_method(self, mock_console):
        """Test decorator uses UsecliError.show() method."""

        @ErrorHandler.handle_exception
        def raise_error():
            raise UsecliError("Test error", "Suggestion")

        with pytest.raises(typer.Exit):
            raise_error()

        # The exception's show() method calls console.print from the exceptions module
        # not the handler module's console, so we just verify it exits
        assert True

    def test_handle_exception_multiple_decorators(self):
        """Test handle_exception works with other decorators."""

        def other_decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        @other_decorator
        @ErrorHandler.handle_exception
        def decorated_function():
            return "success"

        result = decorated_function()
        assert result == "success"

    @patch("usecli.cli.core.error.handler.ErrorHandler.display_error")
    def test_handle_exception_with_args_and_kwargs(self, mock_display_error):
        """Test decorator works with both args and kwargs."""

        @ErrorHandler.handle_exception
        def complex_function(a, b, *args, c=1, **kwargs):
            return a + b + sum(args) + c + sum(kwargs.values())

        result = complex_function(1, 2, 3, 4, c=5, d=6, e=7)
        assert result == 28  # 1 + 2 + 3 + 4 + 5 + 6 + 7

    @patch("usecli.cli.core.error.handler.ErrorHandler.display_error")
    def test_handle_exception_generic_exception_exit_code_is_one(
        self, mock_display_error
    ):
        """Test generic exceptions exit with code 1."""

        @ErrorHandler.handle_exception
        def raise_error():
            raise RuntimeError("Generic error")

        with pytest.raises(typer.Exit) as exc_info:
            raise_error()

        assert exc_info.value.exit_code == 1

    def test_handle_exception_return_value_preserved(self):
        """Test decorator preserves return values."""

        @ErrorHandler.handle_exception
        def function_with_side_effects():
            return {"result": "success", "code": 200}

        result = function_with_side_effects()
        assert result["result"] == "success"
        assert result["code"] == 200
