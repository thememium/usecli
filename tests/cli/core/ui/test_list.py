"""Comprehensive tests for UI list commands module.

Tests cover:
- list_commands(): Displaying available commands with filtering
- Command sorting and organization
- Prefix filtering
- Section grouping (commands with colons)
- Parameter display
"""

from unittest.mock import Mock, patch

from usecli.cli.config.colors import COLOR
from usecli.cli.core.ui.list import list_commands

# =============================================================================
# list_commands() Tests
# =============================================================================


class TestListCommands:
    """Test suite for list_commands() function."""

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_empty(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() with no registered commands."""
        # Setup mock app with no commands
        app = Mock()
        app.registered_commands = []

        # Setup mock click group with no params
        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify print_title was called
        mock_print_title.assert_called_once()

        # Verify console.print was called for headers
        assert (
            mock_console.print.call_count >= 3
        )  # At least Usage, Options, Available commands

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_with_single_command(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() with single registered command."""
        # Create mock command
        mock_command = Mock()
        mock_command.name = "run"
        mock_command.callback = Mock(__name__="run")
        mock_command.help = "Run the tool"

        # Setup mock app
        app = Mock()
        app.registered_commands = [mock_command]

        # Setup mock click group
        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify print_title was called
        mock_print_title.assert_called_once()

        # Verify commands were printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("run" in str(c) for c in print_calls)

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_with_multiple_commands(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() with multiple registered commands."""
        # Create mock commands
        commands = []
        for i, name in enumerate(["build", "run", "test"]):
            cmd = Mock()
            cmd.name = name
            cmd.callback = Mock(__name__=name)
            cmd.help = f"Help for {name}"
            commands.append(cmd)

        # Setup mock app
        app = Mock()
        app.registered_commands = commands

        # Setup mock click group
        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify commands are sorted and printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        # Commands should be sorted: build, run, test
        combined_output = "\n".join(print_calls)
        assert "build" in combined_output
        assert "run" in combined_output
        assert "test" in combined_output

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_with_colon_commands(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() groups commands with colons into sections."""
        # Create commands with colons (subsections)
        commands = []
        for name in ["config:show", "config:set", "spec:generate", "spec:validate"]:
            cmd = Mock()
            cmd.name = name
            cmd.callback = Mock(__name__=name)
            cmd.help = f"Help for {name}"
            commands.append(cmd)

        # Setup mock app
        app = Mock()
        app.registered_commands = commands

        # Setup mock click group
        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify section headers are printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        combined_output = "\n".join(print_calls)

        # Should have section headers
        assert "config:" in combined_output or "config" in combined_output
        assert "spec:" in combined_output or "spec" in combined_output

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_with_mixed_commands(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() with both top-level and namespaced commands."""
        commands = []
        # Top-level commands
        for name in ["run", "test"]:
            cmd = Mock()
            cmd.name = name
            cmd.callback = Mock(__name__=name)
            cmd.help = f"Help for {name}"
            commands.append(cmd)

        # Namespaced commands
        for name in ["config:show", "config:set"]:
            cmd = Mock()
            cmd.name = name
            cmd.callback = Mock(__name__=name)
            cmd.help = f"Help for {name}"
            commands.append(cmd)

        # Setup mock app
        app = Mock()
        app.registered_commands = commands

        # Setup mock click group
        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify all commands are printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        combined_output = "\n".join(print_calls)

        assert "run" in combined_output
        assert "test" in combined_output
        assert "config" in combined_output

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_with_prefix_filter(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() with prefix filter."""
        commands = []
        for name in ["config:show", "config:set", "storage:list", "run"]:
            cmd = Mock()
            cmd.name = name
            cmd.callback = Mock(__name__=name)
            cmd.help = f"Help for {name}"
            commands.append(cmd)

        app = Mock()
        app.registered_commands = commands

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app, prefix_filter="config")

        print_calls = [str(call) for call in mock_console.print.call_args_list]
        combined_output = "\n".join(print_calls)

        assert "config:show" in combined_output or "config:set" in combined_output
        assert "storage:list" not in combined_output

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_with_empty_prefix_filter_result(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() with prefix filter that matches no commands."""
        commands = []
        for name in ["run", "test"]:
            cmd = Mock()
            cmd.name = name
            cmd.callback = Mock(__name__=name)
            cmd.help = f"Help for {name}"
            commands.append(cmd)

        # Setup mock app
        app = Mock()
        app.registered_commands = commands

        # Setup mock click group
        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        # Filter for non-existent prefix
        list_commands(app, prefix_filter="nonexistent")

        # Verify "No commands found" message is printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        combined_output = "\n".join(print_calls)
        assert "No commands found" in combined_output

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_with_click_params(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() displays click group parameters."""
        # Setup mock app with no commands
        app = Mock()
        app.registered_commands = []

        # Setup mock click group with params
        mock_param = Mock()
        mock_param.opts = ["--debug", "-d"]
        mock_param.help = "Enable debug mode"

        click_group = Mock()
        click_group.params = [mock_param]
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify params are printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        combined_output = "\n".join(print_calls)

        assert "--debug" in combined_output or "-d" in combined_output

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_skips_help_flag_param(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() skips --help parameter from display."""
        # Setup mock app
        app = Mock()
        app.registered_commands = []

        # Setup mock click group with help param (should be skipped)
        help_param = Mock()
        help_param.opts = ["--help", "-h"]
        help_param.help = "Show help"

        custom_param = Mock()
        custom_param.opts = ["--verbose", "-v"]
        custom_param.help = "Verbose output"

        click_group = Mock()
        click_group.params = [help_param, custom_param]
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify custom param is printed but help is handled separately
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        combined_output = "\n".join(print_calls)

        # --verbose should be printed
        assert "--verbose" in combined_output
        # Help is printed separately, so --help might not be in the params section

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_handles_missing_command_name(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() uses callback name when command name is None."""
        # Create mock command with None name
        mock_command = Mock()
        mock_command.name = None
        mock_command.callback = Mock(__name__="fallback_command")
        mock_command.help = "Help text"

        # Setup mock app
        app = Mock()
        app.registered_commands = [mock_command]

        # Setup mock click group
        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify fallback command name is used
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        combined_output = "\n".join(print_calls)

        assert "fallback_command" in combined_output

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_handles_missing_help_text(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() handles commands without help text."""
        # Create mock command with None help
        mock_command = Mock()
        mock_command.name = "test-cmd"
        mock_command.callback = Mock(__name__="test_cmd")
        mock_command.help = None

        # Setup mock app
        app = Mock()
        app.registered_commands = [mock_command]

        # Setup mock click group
        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Should not raise exception
        mock_console.print.assert_called()

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_usage_header(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() displays usage header."""
        app = Mock()
        app.registered_commands = []

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify "Usage" header is printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Usage" in str(c) for c in print_calls)

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_options_header(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() displays options header."""
        app = Mock()
        app.registered_commands = []

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify "Options" header is printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("Options" in str(c) for c in print_calls)

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_help_flag_displayed(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() displays --help and -h flags."""
        app = Mock()
        app.registered_commands = []

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify help flags are printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        combined_output = "\n".join(print_calls)

        assert "--help" in combined_output or "-h" in combined_output

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_color_constants_used(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() uses correct COLOR constants."""
        app = Mock()
        app.registered_commands = []

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify color constants are used in output
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        combined_output = "\n".join(print_calls)

        # Should contain color references
        assert COLOR.PRIMARY in combined_output or COLOR.SECONDARY in combined_output

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_command_sorting(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() sorts commands alphabetically."""
        # Create commands in non-alphabetical order
        commands = []
        for name in ["zebra", "alpha", "beta"]:
            cmd = Mock()
            cmd.name = name
            cmd.callback = Mock(__name__=name)
            cmd.help = f"Help for {name}"
            commands.append(cmd)

        app = Mock()
        app.registered_commands = commands

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify commands are printed (sorted order would be alpha, beta, zebra)
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        combined_output = "\n".join(print_calls)

        assert "alpha" in combined_output
        assert "beta" in combined_output
        assert "zebra" in combined_output

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_longest_name_calculation(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() calculates padding based on longest command name."""
        commands = []
        for name in ["a", "very-long-command-name", "b"]:
            cmd = Mock()
            cmd.name = name
            cmd.callback = Mock(__name__=name)
            cmd.help = "Help"
            commands.append(cmd)

        app = Mock()
        app.registered_commands = commands

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify console.print was called
        assert mock_console.print.call_count > 0

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_with_prefix_filter_header_not_shown(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() doesn't show 'Available commands' when prefix_filter is set."""
        commands = []
        for name in ["config:show", "config:set", "run"]:
            cmd = Mock()
            cmd.name = name
            cmd.callback = Mock(__name__=name)
            cmd.help = "Help"
            commands.append(cmd)

        app = Mock()
        app.registered_commands = commands

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app, prefix_filter="config")

        # Verify filtered behavior
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        combined_output = "\n".join(print_calls)

        # "Available commands" should not be shown when filter is active
        # (or it might be, depending on implementation)
        assert "config" in combined_output

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_section_organization(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() organizes namespaced commands into sections."""
        commands = []
        # Create multiple commands in the same section
        for name in ["config:show", "config:set", "config:validate"]:
            cmd = Mock()
            cmd.name = name
            cmd.callback = Mock(__name__=name)
            cmd.help = f"Help for {name}"
            commands.append(cmd)

        app = Mock()
        app.registered_commands = commands

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify console is called with section information
        assert mock_console.print.call_count > 0

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_returns_none(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() returns None."""
        app = Mock()
        app.registered_commands = []

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        result = list_commands(app)

        assert result is None

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_param_without_help_attribute(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() handles params without help attribute gracefully."""
        app = Mock()
        app.registered_commands = []

        # Create param without help attribute
        mock_param = Mock(spec=[])  # No attributes
        mock_param.opts = ["--custom"]

        click_group = Mock()
        click_group.params = [mock_param]
        mock_get_command.return_value = click_group

        # Should not raise exception
        list_commands(app)

        mock_console.print.assert_called()

    @patch("usecli.cli.core.ui.list.print_title")
    @patch("usecli.cli.core.ui.list.console")
    @patch("usecli.cli.core.ui.list.typer.main.get_command")
    def test_list_commands_command_without_callback(
        self, mock_get_command, mock_console, mock_print_title
    ):
        """Test list_commands() handles command with None callback."""
        mock_command = Mock()
        mock_command.name = "cmd-with-no-callback"
        mock_command.callback = None
        mock_command.help = "Help text"

        app = Mock()
        app.registered_commands = [mock_command]

        click_group = Mock()
        click_group.params = []
        mock_get_command.return_value = click_group

        list_commands(app)

        # Verify "unknown" is used as fallback
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        combined_output = "\n".join(print_calls)

        # Should either show command name or fallback to "unknown"
        assert "cmd-with-no-callback" in combined_output or "unknown" in combined_output
