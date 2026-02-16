"""Tests for UsecliValidationError exception class."""

from unittest.mock import MagicMock, patch

from usecli.cli.config.colors import COLOR
from usecli.cli.core.exceptions.base import UsecliError
from usecli.cli.core.exceptions.validation import UsecliValidationError


class TestUsecliValidationError:
    """Test suite for UsecliValidationError class."""

    def test_initialization_with_default_severity(self):
        """Test UsecliValidationError initialization with default severity."""
        message = "Validation failed"
        error = UsecliValidationError(message)

        assert error.message == message
        assert error.severity == "error"
        assert error.suggestion is None
        assert error.exit_code == 1

    def test_initialization_with_warning_severity(self):
        """Test UsecliValidationError initialization with warning severity."""
        message = "This might be wrong"
        error = UsecliValidationError(message, severity="warning")

        assert error.message == message
        assert error.severity == "warning"
        assert error.exit_code == 0  # Warning should have exit code 0

    def test_initialization_with_error_severity(self):
        """Test UsecliValidationError initialization with error severity."""
        message = "This is wrong"
        error = UsecliValidationError(message, severity="error")

        assert error.message == message
        assert error.severity == "error"
        assert error.exit_code == 1  # Error should have exit code 1

    def test_initialization_with_critical_severity(self):
        """Test UsecliValidationError initialization with critical severity."""
        message = "Critical failure"
        error = UsecliValidationError(message, severity="critical")

        assert error.message == message
        assert error.severity == "critical"
        assert error.exit_code == 1  # Critical should have exit code 1

    def test_initialization_with_suggestion(self):
        """Test UsecliValidationError initialization with suggestion."""
        message = "Validation failed"
        suggestion = "Check your input format"
        error = UsecliValidationError(message, suggestion=suggestion)

        assert error.message == message
        assert error.suggestion == suggestion

    def test_initialization_with_all_parameters(self):
        """Test UsecliValidationError initialization with all parameters."""
        message = "Validation failed"
        severity = "warning"
        suggestion = "Check your input format"
        error = UsecliValidationError(message, severity, suggestion)

        assert error.message == message
        assert error.severity == severity
        assert error.suggestion == suggestion

    def test_inherits_from_usecli_error(self):
        """Test UsecliValidationError inherits from UsecliError."""
        error = UsecliValidationError("Test")
        assert isinstance(error, UsecliError)

    def test_severity_styles_mapping(self):
        """Test SEVERITY_STYLES contains expected severity levels."""
        assert "warning" in UsecliValidationError.SEVERITY_STYLES
        assert "error" in UsecliValidationError.SEVERITY_STYLES
        assert "critical" in UsecliValidationError.SEVERITY_STYLES

    def test_severity_styles_warning_structure(self):
        """Test warning severity style structure."""
        warning_style = UsecliValidationError.SEVERITY_STYLES["warning"]
        assert "color" in warning_style
        assert "icon" in warning_style
        assert warning_style["color"] == COLOR.WARNING
        assert warning_style["icon"] == "⚠"

    def test_severity_styles_error_structure(self):
        """Test error severity style structure."""
        error_style = UsecliValidationError.SEVERITY_STYLES["error"]
        assert "color" in error_style
        assert "icon" in error_style
        assert error_style["color"] == COLOR.ERROR
        assert error_style["icon"] == "✗"

    def test_severity_styles_critical_structure(self):
        """Test critical severity style structure."""
        critical_style = UsecliValidationError.SEVERITY_STYLES["critical"]
        assert "color" in critical_style
        assert "icon" in critical_style
        assert critical_style["color"] == COLOR.ERROR
        assert critical_style["icon"] == "☠"

    def test_warning_severity_sets_exit_code_0(self):
        """Test warning severity sets exit_code to 0."""
        error = UsecliValidationError("Warning", severity="warning")
        assert error.exit_code == 0

    def test_error_severity_sets_exit_code_1(self):
        """Test error severity sets exit_code to 1."""
        error = UsecliValidationError("Error", severity="error")
        assert error.exit_code == 1

    def test_critical_severity_sets_exit_code_1(self):
        """Test critical severity sets exit_code to 1."""
        error = UsecliValidationError("Critical", severity="critical")
        assert error.exit_code == 1

    def test_unknown_severity_defaults_to_error(self):
        """Test unknown severity defaults to error styling."""
        error = UsecliValidationError("Test", severity="unknown")
        # Should use error style as default
        assert error.color == COLOR.ERROR
        assert error.icon == "✗"

    def test_icon_and_color_set_from_severity_styles(self):
        """Test icon and color are set from SEVERITY_STYLES."""
        error_warning = UsecliValidationError("Test", severity="warning")
        assert error_warning.icon == "⚠"
        assert error_warning.color == COLOR.WARNING

        error_error = UsecliValidationError("Test", severity="error")
        assert error_error.icon == "✗"
        assert error_error.color == COLOR.ERROR

        error_critical = UsecliValidationError("Test", severity="critical")
        assert error_critical.icon == "☠"
        assert error_critical.color == COLOR.ERROR

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_without_suggestion(self, mock_console):
        """Test show() method without suggestion."""
        message = "Validation failed"
        error = UsecliValidationError(message)
        error.show()

        # Verify console.print was called once
        assert mock_console.print.call_count == 1

        # Verify message contains icon and styled message
        call_args = mock_console.print.call_args[0][0]
        assert "✗" in call_args
        assert "Validation failed" in call_args

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_with_suggestion(self, mock_console):
        """Test show() method with suggestion."""
        message = "Validation failed"
        suggestion = "Please check your input"
        error = UsecliValidationError(message, suggestion=suggestion)
        error.show()

        # Verify console.print was called twice
        assert mock_console.print.call_count == 2

        # Verify first call contains error message
        first_call = mock_console.print.call_args_list[0][0][0]
        assert "✗" in first_call
        assert "Validation failed" in first_call

        # Verify second call contains suggestion
        second_call = mock_console.print.call_args_list[1][0][0]
        assert "💡" in second_call
        assert "Please check your input" in second_call

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_warning_severity(self, mock_console):
        """Test show() with warning severity."""
        message = "Warning message"
        error = UsecliValidationError(message, severity="warning")
        error.show()

        call_args = mock_console.print.call_args[0][0]
        assert "⚠" in call_args
        assert COLOR.WARNING in call_args

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_error_severity(self, mock_console):
        """Test show() with error severity."""
        message = "Error message"
        error = UsecliValidationError(message, severity="error")
        error.show()

        call_args = mock_console.print.call_args[0][0]
        assert "✗" in call_args
        assert COLOR.ERROR in call_args

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_critical_severity(self, mock_console):
        """Test show() with critical severity."""
        message = "Critical message"
        error = UsecliValidationError(message, severity="critical")
        error.show()

        call_args = mock_console.print.call_args[0][0]
        assert "☠" in call_args
        assert COLOR.ERROR in call_args

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_icon_styling_correct(self, mock_console):
        """Test show() applies correct styling to icon."""
        error = UsecliValidationError("Test", severity="warning")
        error.show()

        call_args = mock_console.print.call_args[0][0]
        assert f"[bold {COLOR.WARNING}]⚠[/bold {COLOR.WARNING}]" in call_args

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_message_styling_correct(self, mock_console):
        """Test show() applies correct styling to message."""
        error = UsecliValidationError("Warning text", severity="warning")
        error.show()

        call_args = mock_console.print.call_args[0][0]
        assert f"[bold {COLOR.WARNING}]Warning text[/bold {COLOR.WARNING}]" in call_args

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_suggestion_styling_correct(self, mock_console):
        """Test show() applies correct styling to suggestion."""
        suggestion = "Try this"
        error = UsecliValidationError("Test", suggestion=suggestion)
        error.show()

        suggestion_call = mock_console.print.call_args_list[1][0][0]
        assert (
            f"[dim {COLOR.WARNING}]💡 {suggestion}[/dim {COLOR.WARNING}]"
            in suggestion_call
        )

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_with_file_parameter(self, mock_console):
        """Test show() method accepts file parameter."""
        error = UsecliValidationError("Test error")
        file_obj = MagicMock()

        # Should not raise an exception
        error.show(file=file_obj)

        # Verify console.print was called
        assert mock_console.print.called

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_all_severity_levels(self, mock_console):
        """Test show() works with all severity levels."""
        severities = ["warning", "error", "critical"]
        for severity in severities:
            mock_console.reset_mock()
            error = UsecliValidationError("Test", severity=severity)
            error.show()
            assert mock_console.print.called

    def test_multiple_instances_independent(self):
        """Test multiple UsecliValidationError instances are independent."""
        error1 = UsecliValidationError("Error 1", "warning", "Suggestion 1")
        error2 = UsecliValidationError("Error 2", "error", "Suggestion 2")
        error3 = UsecliValidationError("Error 3", "critical", "Suggestion 3")

        assert error1.severity == "warning"
        assert error1.exit_code == 0
        assert error2.severity == "error"
        assert error2.exit_code == 1
        assert error3.severity == "critical"
        assert error3.exit_code == 1

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_with_empty_message(self, mock_console):
        """Test show() with empty message."""
        error = UsecliValidationError("")
        error.show()

        assert mock_console.print.called

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_with_long_message(self, mock_console):
        """Test show() with long message."""
        long_message = "C" * 500
        error = UsecliValidationError(long_message)
        error.show()

        call_args = mock_console.print.call_args[0][0]
        assert "C" * 500 in call_args

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_with_unicode_message(self, mock_console):
        """Test show() with unicode characters."""
        message = "Error with émojis 🚀 and spëcial chars"
        error = UsecliValidationError(message)
        error.show()

        assert mock_console.print.called

    def test_severity_case_sensitive(self):
        """Test severity parameter is case-sensitive."""
        error_lower = UsecliValidationError("Test", severity="warning")
        assert error_lower.severity == "warning"

        # Unknown case should default to error
        error_upper = UsecliValidationError("Test", severity="WARNING")
        assert error_upper.color == COLOR.ERROR  # Defaults to error

    def test_exit_code_only_warning_is_zero(self):
        """Test only warning severity has exit_code 0."""
        warning = UsecliValidationError("Test", severity="warning")
        error = UsecliValidationError("Test", severity="error")
        critical = UsecliValidationError("Test", severity="critical")

        assert warning.exit_code == 0
        assert error.exit_code == 1
        assert critical.exit_code == 1

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_multiple_calls(self, mock_console):
        """Test show() can be called multiple times."""
        error = UsecliValidationError("Test", "warning", "Suggestion")
        error.show()
        error.show()

        # Both calls should succeed
        assert mock_console.print.call_count >= 4  # 2 per call

    @patch("usecli.cli.core.exceptions.validation.console")
    def test_show_severity_stored_and_reused(self, mock_console):
        """Test severity level is stored and used consistently."""
        error = UsecliValidationError("Test", severity="critical")

        # Call show multiple times
        error.show()
        error.show()

        # All calls should use critical icon
        for call in mock_console.print.call_args_list:
            if call[0]:  # Non-empty calls
                call_text = str(call[0][0])
                if "Test" in call_text:  # The message call
                    assert "☠" in call_text
