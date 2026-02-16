"""Tests for UsecliConfigError exception class."""

from unittest.mock import MagicMock, patch

from usecli.cli.config.colors import COLOR
from usecli.cli.core.exceptions.base import UsecliError
from usecli.cli.core.exceptions.config import UsecliConfigError


class TestUsecliConfigError:
    """Test suite for UsecliConfigError class."""

    def test_initialization_with_message_only(self):
        """Test UsecliConfigError initialization with message only."""
        message = "Invalid configuration"
        error = UsecliConfigError(message)

        assert error.message == message
        assert error.config_file is None
        assert error.suggestion is None
        assert error.exit_code == 1

    def test_initialization_with_config_file(self):
        """Test UsecliConfigError initialization with config file."""
        message = "Invalid configuration"
        config_file = "/path/to/config.yml"
        error = UsecliConfigError(message, config_file=config_file)

        assert error.message == message
        assert error.config_file == config_file
        assert error.suggestion is None

    def test_initialization_with_suggestion(self):
        """Test UsecliConfigError initialization with suggestion."""
        message = "Invalid configuration"
        suggestion = "Run 'usecli config init'"
        error = UsecliConfigError(message, suggestion=suggestion)

        assert error.message == message
        assert error.suggestion == suggestion
        assert error.config_file is None

    def test_initialization_with_all_parameters(self):
        """Test UsecliConfigError initialization with all parameters."""
        message = "Invalid configuration"
        config_file = "/path/to/config.yml"
        suggestion = "Run 'usecli config init'"
        error = UsecliConfigError(message, config_file, suggestion)

        assert error.message == message
        assert error.config_file == config_file
        assert error.suggestion == suggestion

    def test_inherits_from_usecli_error(self):
        """Test UsecliConfigError inherits from UsecliError."""
        error = UsecliConfigError("Test error")
        assert isinstance(error, UsecliError)

    def test_exit_code_is_inherited(self):
        """Test exit_code is inherited from UsecliError."""
        error = UsecliConfigError("Test error")
        assert error.exit_code == 1

    @patch("usecli.cli.core.exceptions.config.console")
    def test_show_without_config_file_or_suggestion(self, mock_console):
        """Test show() method without config_file or suggestion."""
        message = "Invalid configuration format"
        error = UsecliConfigError(message)
        error.show()

        # Verify console.rule was called once for the header
        assert mock_console.rule.call_count == 1

        # Verify console.print was called once for the error message
        assert mock_console.print.call_count == 1

        # Verify rule contains correct title and styling
        rule_call = mock_console.rule.call_args
        assert "Configuration Error" in rule_call.kwargs.get("title", "")
        assert COLOR.ERROR in rule_call.kwargs.get("title", "")
        assert rule_call.kwargs.get("style") == COLOR.ERROR
        assert rule_call.kwargs.get("align") == "left"

    @patch("usecli.cli.core.exceptions.config.console")
    def test_show_with_config_file(self, mock_console):
        """Test show() method with config_file."""
        message = "Invalid configuration format"
        config_file = "/etc/usecli/config.yml"
        error = UsecliConfigError(message, config_file=config_file)
        error.show()

        # Verify console.rule was called
        assert mock_console.rule.called

        # Verify config file was printed
        print_calls_str = " ".join(
            str(call) for call in mock_console.print.call_args_list
        )
        assert config_file in print_calls_str

    @patch("usecli.cli.core.exceptions.config.console")
    def test_show_with_suggestion(self, mock_console):
        """Test show() method with suggestion."""
        message = "Invalid configuration format"
        suggestion = "Use 'usecli config validate' to check your configuration"
        error = UsecliConfigError(message, suggestion=suggestion)
        error.show()

        # Verify suggestion was printed
        print_calls = [call[0][0] for call in mock_console.print.call_args_list]
        suggestion_printed = any(suggestion in str(call) for call in print_calls)
        assert suggestion_printed

    @patch("usecli.cli.core.exceptions.config.console")
    def test_show_with_all_parameters(self, mock_console):
        """Test show() method with all parameters."""
        message = "Invalid configuration format"
        config_file = "/etc/usecli/config.yml"
        suggestion = "Use 'usecli config validate' to check your configuration"
        error = UsecliConfigError(message, config_file, suggestion)
        error.show()

        # Verify console.rule was called
        assert mock_console.rule.called

        # Verify all elements were printed
        all_calls_str = " ".join(
            str(call) for call in mock_console.print.call_args_list
        )

        assert message in all_calls_str
        assert config_file in all_calls_str
        assert suggestion in all_calls_str

    @patch("usecli.cli.core.exceptions.config.console")
    def test_show_rule_title_contains_error_color(self, mock_console):
        """Test show() rule title is colored with ERROR color."""
        error = UsecliConfigError("Test")
        error.show()

        rule_call = mock_console.rule.call_args
        title = rule_call.kwargs.get("title", "")
        assert f"[bold {COLOR.ERROR}]" in title
        assert f"[/bold {COLOR.ERROR}]" in title

    @patch("usecli.cli.core.exceptions.config.console")
    def test_show_file_text_contains_foreground_muted_color(self, mock_console):
        """Test show() file text uses FOREGROUND_MUTED color."""
        config_file = "/path/to/config.yml"
        error = UsecliConfigError("Test", config_file=config_file)
        error.show()

        # Find the print call that contains the config file
        print_calls = mock_console.print.call_args_list
        file_call = next(
            (call for call in print_calls if config_file in str(call)), None
        )
        assert file_call is not None

        call_text = file_call[0][0]
        assert COLOR.FOREGROUND_MUTED in call_text

    @patch("usecli.cli.core.exceptions.config.console")
    def test_show_error_message_has_bold_error_color(self, mock_console):
        """Test show() error message uses bold ERROR color."""
        message = "Invalid configuration"
        error = UsecliConfigError(message)
        error.show()

        # Find the print call that contains the error message
        print_calls = mock_console.print.call_args_list
        message_call = next(
            (call for call in print_calls if message in str(call)), None
        )
        assert message_call is not None

        call_text = message_call[0][0]
        assert f"[bold {COLOR.ERROR}]" in call_text

    @patch("usecli.cli.core.exceptions.config.console")
    def test_show_suggestion_has_warning_color(self, mock_console):
        """Test show() suggestion uses WARNING color."""
        suggestion = "Try this fix"
        error = UsecliConfigError("Test", suggestion=suggestion)
        error.show()

        # Find the print call that contains the suggestion
        print_calls = mock_console.print.call_args_list
        suggestion_call = next(
            (call for call in print_calls if suggestion in str(call)), None
        )
        assert suggestion_call is not None

        call_text = suggestion_call[0][0]
        assert f"[dim {COLOR.WARNING}]" in call_text

    @patch("usecli.cli.core.exceptions.config.console")
    def test_show_with_file_parameter(self, mock_console):
        """Test show() method accepts file parameter."""
        error = UsecliConfigError("Test error")
        file_obj = MagicMock()

        # Should not raise an exception
        error.show(file=file_obj)

        # Verify console.rule was called
        assert mock_console.rule.called

    def test_config_file_can_be_none(self):
        """Test config_file can be None (default)."""
        error = UsecliConfigError("Test", config_file=None)
        assert error.config_file is None

    def test_config_file_can_be_path_string(self):
        """Test config_file can store path strings."""
        paths = [
            "/etc/usecli/config.yml",
            "~/.usecli/config.yaml",
            "./config.toml",
            "C:\\Users\\name\\.usecli\\config.yml",
        ]
        for path in paths:
            error = UsecliConfigError("Test", config_file=path)
            assert error.config_file == path

    @patch("usecli.cli.core.exceptions.config.console")
    def test_show_empty_suggestion(self, mock_console):
        """Test show() with empty suggestion string."""
        error = UsecliConfigError("Test", suggestion="")
        error.show()

        # With empty suggestion, it should still print
        # but the suggestion won't have meaningful content
        print_calls = mock_console.print.call_args_list
        # Should have at least rule and error message
        assert len(print_calls) >= 1

    @patch("usecli.cli.core.exceptions.config.console")
    def test_show_empty_config_file(self, mock_console):
        """Test show() with empty config_file string."""
        error = UsecliConfigError("Test", config_file="")
        error.show()

        # With empty config_file, it should still be processed
        # but may not print file info since it's falsy
        assert mock_console.print.called

    @patch("usecli.cli.core.exceptions.config.console")
    def test_show_multiple_calls(self, mock_console):
        """Test show() can be called multiple times."""
        error = UsecliConfigError(
            "Test", config_file="/path/config.yml", suggestion="Fix it"
        )
        error.show()
        error.show()

        # Both calls should succeed
        assert mock_console.rule.call_count >= 2

    def test_multiple_instances_independent(self):
        """Test multiple UsecliConfigError instances are independent."""
        error1 = UsecliConfigError("Error 1", "/path1.yml", "Suggestion 1")
        error2 = UsecliConfigError("Error 2", "/path2.yml", "Suggestion 2")

        assert error1.message == "Error 1"
        assert error1.config_file == "/path1.yml"
        assert error2.message == "Error 2"
        assert error2.config_file == "/path2.yml"
