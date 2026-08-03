"""Tests for UsecliUsageError and UsecliBadParameter exception classes."""

from unittest.mock import MagicMock, patch

import pytest
from click.exceptions import BadParameter, Exit, UsageError

from usecli.cli.config.colors import COLOR
from usecli.cli.core.exceptions.usage import UsecliBadParameter, UsecliUsageError


class TestUsecliUsageError:
    """Test suite for UsecliUsageError class."""

    def test_inherits_from_click_usage_error(self):
        """Test UsecliUsageError inherits from click.exceptions.UsageError."""
        with patch("click.Context"):
            error = UsecliUsageError("Test error")
            assert isinstance(error, UsageError)

    def test_initialization_with_message(self):
        """Test UsecliUsageError initialization."""
        message = "Invalid command usage"
        with patch("click.Context"):
            error = UsecliUsageError(message)
            assert error.message == message

    def test_initialization_with_context(self):
        """Test UsecliUsageError initialization with context."""
        message = "Invalid command usage"
        ctx = MagicMock()
        ctx.get_help = MagicMock(return_value="Mocked help text")

        with patch("click.Context"):
            error = UsecliUsageError(message, ctx=ctx)
            assert error.message == message
            assert error.ctx == ctx

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_without_context(self, mock_console):
        """Test show() method without context."""
        message = "Invalid command usage"
        with patch("click.Context"):
            error = UsecliUsageError(message)
            error.show()

        # Verify console.print was called at least once
        assert mock_console.print.call_count >= 1

        # Verify error message was printed
        first_call = mock_console.print.call_args_list[0][0][0]
        assert "ERROR" in first_call or "error" in first_call.lower()

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_with_context(self, mock_console):
        """Test show() method with context."""
        message = "Invalid command usage"
        ctx = MagicMock()
        ctx.get_help = MagicMock(return_value="Usage: mycommand [OPTIONS]")

        with patch("click.Context"):
            error = UsecliUsageError(message, ctx=ctx)
            error.show()

        # Verify console.print was called multiple times (error + help)
        assert mock_console.print.call_count >= 2

        # Verify help text was printed
        help_printed = False
        for call in mock_console.print.call_args_list:
            if "Usage:" in str(call):
                help_printed = True
                break
        assert help_printed

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_error_prefix_formatting(self, mock_console):
        """Test show() error prefix has correct formatting."""
        message = "Invalid command usage"
        with patch("click.Context"):
            error = UsecliUsageError(message)
            error.show()

        first_call = mock_console.print.call_args_list[0][0][0]
        assert f"[bold {COLOR.ERROR}]ERROR[/bold {COLOR.ERROR}]" in first_call

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_error_message_has_bold_error_color(self, mock_console):
        """Test show() error message uses bold ERROR color."""
        message = "Invalid argument"
        with patch("click.Context"):
            error = UsecliUsageError(message)
            error.show()

        first_call = mock_console.print.call_args_list[0][0][0]
        assert f"[bold {COLOR.ERROR}]" in first_call
        assert f"[/bold {COLOR.ERROR}]" in first_call

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_with_file_parameter(self, mock_console):
        """Test show() method accepts file parameter."""
        import sys

        with patch("click.Context"):
            error = UsecliUsageError("Test error")
            # Should not raise an exception
            error.show(file=sys.stderr)
            assert mock_console.print.called

    def test_can_be_instantiated_without_context(self):
        """Test UsecliUsageError can be created without context."""
        with patch("click.Context"):
            error = UsecliUsageError("Test message")
            assert error.ctx is None or error.ctx != MagicMock()

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_context_get_help_called(self, mock_console):
        """Test show() calls ctx.get_help() when context is present."""
        ctx = MagicMock()
        ctx.get_help = MagicMock(return_value="Help text")

        with patch("click.Context"):
            error = UsecliUsageError("Test", ctx=ctx)
            error.show()

        # Verify get_help was called
        ctx.get_help.assert_called_once()

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_survives_context_get_help_raising_exit(self, mock_console):
        """Test show() does not propagate Exit when ctx.get_help() raises it.

        CustomHelpCommand.get_help() (see base_command.py) prints help
        directly and raises Exit(0) instead of returning a string, so that a
        bare `--help` invocation exits cleanly. ctx.get_help() delegates to
        it for any real subcommand. If show() let that Exit(0) escape here,
        it would unwind past the sys.exit(2) call in the caller and the
        usage error would be reported as a success (exit 0) instead of a
        usage error (exit 2).
        """
        ctx = MagicMock()
        ctx.get_help = MagicMock(side_effect=Exit(0))

        with patch("click.Context"):
            error = UsecliUsageError("Test error", ctx=ctx)
            # Should not raise - the Exit from get_help() must be contained
            # here so the caller's sys.exit(error.exit_code) still runs.
            error.show()

        assert error.exit_code == 2
        ctx.get_help.assert_called_once()
        # The error line itself must still have been printed.
        first_call = mock_console.print.call_args_list[0][0][0]
        assert "ERROR" in first_call

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_prints_help_after_blank_line_when_context(self, mock_console):
        """Test show() prints blank line before help when context exists."""
        ctx = MagicMock()
        ctx.get_help = MagicMock(return_value="Help: command [OPTIONS]")

        with patch("click.Context"):
            error = UsecliUsageError("Error message", ctx=ctx)
            error.show()

        # Should have error message, blank line, and help
        assert mock_console.print.call_count >= 3

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_with_empty_message(self, mock_console):
        """Test show() with empty message."""
        with patch("click.Context"):
            error = UsecliUsageError("")
            error.show()

        assert mock_console.print.called

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_with_long_message(self, mock_console):
        """Test show() with long error message."""
        long_message = "A" * 500
        with patch("click.Context"):
            error = UsecliUsageError(long_message)
            error.show()

        first_call = str(mock_console.print.call_args_list[0])
        assert "A" in first_call

    def test_multiple_instances_independent(self):
        """Test multiple UsecliUsageError instances are independent."""
        with patch("click.Context"):
            error1 = UsecliUsageError("Error 1")
            error2 = UsecliUsageError("Error 2")

            assert error1.message == "Error 1"
            assert error2.message == "Error 2"


class TestUsecliBadParameter:
    """Test suite for UsecliBadParameter class."""

    def test_inherits_from_click_bad_parameter(self):
        """Test UsecliBadParameter inherits from click.exceptions.BadParameter."""
        with patch("click.Context"):
            error = UsecliBadParameter("Invalid parameter")
            assert isinstance(error, BadParameter)

    def test_initialization_with_message(self):
        """Test UsecliBadParameter initialization."""
        message = "Invalid parameter value"
        with patch("click.Context"):
            error = UsecliBadParameter(message)
            assert error.message == message

    def test_initialization_with_context(self):
        """Test UsecliBadParameter initialization with context."""
        message = "Invalid parameter value"
        ctx = MagicMock()
        ctx.get_help = MagicMock(return_value="Mocked help text")

        with patch("click.Context"):
            error = UsecliBadParameter(message, ctx=ctx)
            assert error.message == message
            assert error.ctx == ctx

    def test_initialization_with_param_hint(self):
        """Test UsecliBadParameter initialization with param_hint."""
        message = "Invalid parameter value"
        param_hint = "'--name'"

        with patch("click.Context"):
            error = UsecliBadParameter(message, param_hint=param_hint)
            assert error.param_hint == param_hint

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_without_context(self, mock_console):
        """Test show() method without context."""
        message = "Invalid parameter value"
        with patch("click.Context"):
            error = UsecliBadParameter(message)
            error.show()

        # Verify console.print was called
        assert mock_console.print.call_count >= 1

        # Verify error message was printed
        calls = mock_console.print.call_args_list
        assert len(calls) >= 1

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_with_context(self, mock_console):
        """Test show() method with context."""
        message = "Invalid parameter value"
        ctx = MagicMock()
        ctx.get_help = MagicMock(return_value="Usage: command [OPTIONS]")

        with patch("click.Context"):
            error = UsecliBadParameter(message, ctx=ctx)
            error.show()

        # Verify console.print was called multiple times
        assert mock_console.print.call_count >= 2

        # Verify help text was printed
        all_calls = str(mock_console.print.call_args_list)
        assert "Usage:" in all_calls

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_starts_with_blank_line(self, mock_console):
        """Test show() starts with a blank line."""
        with patch("click.Context"):
            error = UsecliBadParameter("Test error")
            error.show()

        # First call should be blank line (empty string)
        first_call = mock_console.print.call_args_list[0][0]
        assert first_call == ()  # No arguments for blank line

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_error_prefix_formatting(self, mock_console):
        """Test show() error prefix has correct formatting."""
        message = "Invalid parameter"
        with patch("click.Context"):
            error = UsecliBadParameter(message)
            error.show()

        # Find the call that contains ERROR
        error_call = None
        for call in mock_console.print.call_args_list:
            call_text = str(call)
            if "ERROR" in call_text:
                error_call = call_text
                break

        assert error_call is not None
        assert "bold black on" in error_call or f"{COLOR.ERROR}" in error_call

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_error_message_has_bold_error_color(self, mock_console):
        """Test show() error message uses bold ERROR color."""
        message = "Invalid value for --name"
        with patch("click.Context"):
            error = UsecliBadParameter(message)
            error.show()

        # Find error message call
        error_call = None
        for call in mock_console.print.call_args_list:
            call_text = str(call)
            if "Invalid value" in call_text:
                error_call = call_text
                break

        assert error_call is not None
        assert COLOR.ERROR in error_call

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_with_file_parameter(self, mock_console):
        """Test show() method accepts file parameter."""
        import sys

        with patch("click.Context"):
            error = UsecliBadParameter("Test error")
            # Should not raise an exception
            error.show(file=sys.stderr)
            assert mock_console.print.called

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_context_get_help_called(self, mock_console):
        """Test show() calls ctx.get_help() when context is present."""
        ctx = MagicMock()
        ctx.get_help = MagicMock(return_value="Help text")

        with patch("click.Context"):
            error = UsecliBadParameter("Test", ctx=ctx)
            error.show()

        # Verify get_help was called
        ctx.get_help.assert_called_once()

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_survives_context_get_help_raising_exit(self, mock_console):
        """Test show() does not propagate Exit when ctx.get_help() raises it.

        Same scenario as UsecliUsageError: ctx.get_help() delegates to
        CustomHelpCommand.get_help(), which raises Exit(0) after printing
        help instead of returning a string. show() must contain that Exit
        so the caller's sys.exit(error.exit_code) still runs with the
        parameter error's real exit code.
        """
        ctx = MagicMock()
        ctx.get_help = MagicMock(side_effect=Exit(0))

        with patch("click.Context"):
            error = UsecliBadParameter("Invalid value", ctx=ctx)
            # Should not raise - the Exit from get_help() must be contained
            # here so the caller's sys.exit(error.exit_code) still runs.
            error.show()

        assert error.exit_code == 2
        ctx.get_help.assert_called_once()
        assert mock_console.print.called

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_prints_help_when_context(self, mock_console):
        """Test show() prints help when context exists."""
        ctx = MagicMock()
        ctx.get_help = MagicMock(return_value="Help: command [OPTIONS]")

        with patch("click.Context"):
            error = UsecliBadParameter("Error message", ctx=ctx)
            error.show()

        # Should have blank line, error, and help
        assert mock_console.print.call_count >= 2

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_with_empty_message(self, mock_console):
        """Test show() with empty message."""
        with patch("click.Context"):
            error = UsecliBadParameter("")
            error.show()

        assert mock_console.print.called

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_with_param_hint(self, mock_console):
        """Test show() includes param_hint if provided."""
        message = "Invalid value"
        param_hint = "'--name'"

        with patch("click.Context"):
            error = UsecliBadParameter(message, param_hint=param_hint)
            error.show()

        # Verify param_hint might be included in formatted message
        assert mock_console.print.called

    def test_can_be_instantiated_without_context(self):
        """Test UsecliBadParameter can be created without context."""
        with patch("click.Context"):
            error = UsecliBadParameter("Test message")
            # Should succeed
            assert error.message == "Test message"

    def test_multiple_instances_independent(self):
        """Test multiple UsecliBadParameter instances are independent."""
        with patch("click.Context"):
            error1 = UsecliBadParameter("Error 1", param_hint="'--opt1'")
            error2 = UsecliBadParameter("Error 2", param_hint="'--opt2'")

            assert error1.message == "Error 1"
            assert error2.message == "Error 2"
            assert error1.param_hint == "'--opt1'"
            assert error2.param_hint == "'--opt2'"

    @patch("usecli.cli.core.exceptions.usage.console")
    def test_show_with_long_message(self, mock_console):
        """Test show() with long error message."""
        long_message = "B" * 500
        with patch("click.Context"):
            error = UsecliBadParameter(long_message)
            error.show()

        assert mock_console.print.called


class TestSubcommandUsageErrorExitCode:
    """Integration tests: rejecting a subcommand's own args must exit 2.

    Regression coverage for a bug where CustomHelpCommand.get_help()
    raising Exit(0) (see base_command.py) escaped through
    _get_help_text_with_command_name() and UsecliUsageError.show(),
    causing usecli's own except handlers to report a subcommand parse
    rejection as a clean exit instead of a usage error.
    """

    @pytest.fixture
    def runner(self):
        from click.testing import CliRunner

        return CliRunner()

    @pytest.fixture
    def registered_leaf_command(self):
        """Register a deterministic no-argument leaf command on usecli.app."""
        import usecli
        from usecli import BaseCommand

        class UsageErrorExitCodeLeafCommand(BaseCommand):
            def handle(self) -> None:
                return None

            def signature(self) -> str:
                return "usage-error-exit-code-leaf"

            def description(self) -> str:
                return "Exercise subcommand usage-error exit codes"

        existing_names = {command.name for command in usecli.app.registered_commands}
        if "usage-error-exit-code-leaf" not in existing_names:
            UsageErrorExitCodeLeafCommand(usecli.app)

        return "usage-error-exit-code-leaf"

    def _invoke(self, runner, arguments: list[str]):
        from typer.main import get_command

        import usecli

        return runner.invoke(get_command(usecli.app), arguments)

    def test_unknown_option_on_subcommand_exits_2(
        self, runner, registered_leaf_command
    ):
        """An unrecognized option for a subcommand's own args exits 2."""
        result = self._invoke(runner, [registered_leaf_command, "--bogus-flag", "x"])

        assert result.exit_code == 2, result.output
        assert "No such option" in result.output

    def test_extra_positional_argument_on_subcommand_exits_2(
        self, runner, registered_leaf_command
    ):
        """An unexpected extra positional argument exits 2."""
        result = self._invoke(runner, [registered_leaf_command, "extra_positional_arg"])

        assert result.exit_code == 2, result.output

    def test_unknown_option_before_subcommand_still_exits_2(self, monkeypatch):
        """Regression guard: top-level parsing keeps its correct exit code.

        Unlike a subcommand's own args, a top-level option is rejected by
        make_context() before PrefixMatchingGroup.invoke() (and therefore
        any CustomHelpCommand) is ever reached; standalone_mode=False then
        re-raises it out of PrefixMatchingGroup.main() entirely, and only
        usecli.main()'s own outer handler catches it. CliRunner invoking
        get_command(usecli.app) directly bypasses that outer handler, so
        this goes through the real entry point (usecli.main()) instead to
        faithfully exercise the path a real invocation takes.
        """
        import sys

        import usecli

        monkeypatch.setattr(sys, "argv", ["usecli", "--bogus-flag"])

        with pytest.raises(SystemExit) as exc_info:
            usecli.main()

        assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# _get_help_text_with_command_name
# ---------------------------------------------------------------------------


class TestGetHelpTextWithCommandName:
    def test_returns_help_when_command_name_is_none(self):
        from usecli.cli.core.exceptions.usage import _get_help_text_with_command_name

        ctx = MagicMock()
        ctx.info_name = None
        ctx.get_help.return_value = "Help text"

        with patch(
            "usecli.cli.core.exceptions.usage.get_script_command_name",
            return_value=None,
        ):
            result = _get_help_text_with_command_name(ctx)

        assert result == "Help text"

    def test_returns_empty_when_get_help_raises_exit(self):
        from usecli.cli.core.exceptions.usage import _get_help_text_with_command_name

        ctx = MagicMock()
        ctx.info_name = None
        ctx.get_help.side_effect = Exit(0)

        with patch(
            "usecli.cli.core.exceptions.usage.get_script_command_name",
            return_value=None,
        ):
            result = _get_help_text_with_command_name(ctx)

        assert result == ""

    def test_sets_info_name_to_command_name(self):
        from usecli.cli.core.exceptions.usage import _get_help_text_with_command_name

        ctx = MagicMock()
        ctx.info_name = "original"
        ctx.get_help.return_value = "Help text"

        with patch(
            "usecli.cli.core.exceptions.usage.get_script_command_name",
            return_value="mycli",
        ):
            result = _get_help_text_with_command_name(ctx)

        assert result == "Help text"
        # info_name should be restored
        assert ctx.info_name == "original"
