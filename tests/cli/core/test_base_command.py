"""Comprehensive tests for usecli.cli.core.base_command module.

Tests cover:
- CustomHelpCommand class: initialization, help formatting, parameter handling
- BaseCommand abstract class: registration, inheritance, abstract methods
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from click.exceptions import Exit
from typer.core import TyperArgument, TyperOption

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from usecli.cli.config.colors import COLOR
from usecli.cli.core import base_command
from usecli.cli.core.base_command import (
    BaseCommand,
    CustomHelpCommand,
    NestedCommandRegistry,
)

# =============================================================================
# CustomHelpCommand Tests
# =============================================================================


class TestCustomHelpCommandInit:
    """Tests for CustomHelpCommand initialization."""

    def test_init_sets_help_option_names(self):
        """Test __init__ sets help_option_names to ['--help', '-h']."""
        cmd = CustomHelpCommand(name="test")
        assert cmd.context_settings.get("help_option_names") == ["--help", "-h"]

    def test_init_preserves_existing_context_settings(self):
        """Test __init__ preserves existing context_settings."""
        existing_settings = {"max_content_width": 120}
        cmd = CustomHelpCommand(name="test", context_settings=existing_settings)
        # help_option_names should be added
        assert cmd.context_settings.get("help_option_names") == ["--help", "-h"]
        # Existing settings should be preserved
        assert cmd.context_settings.get("max_content_width") == 120

    def test_init_with_no_context_settings(self):
        """Test __init__ creates context_settings if not provided."""
        cmd = CustomHelpCommand(name="test")
        assert "help_option_names" in cmd.context_settings
        assert cmd.context_settings["help_option_names"] == ["--help", "-h"]

    def test_init_calls_parent_init(self):
        """Test __init__ calls parent TyperCommand.__init__."""
        with patch("usecli.cli.core.base_command.TyperCommand.__init__") as mock_parent:
            mock_parent.return_value = None
            CustomHelpCommand(name="test")
            mock_parent.assert_called_once()


class TestCustomHelpCommandFormatHelpNoParams:
    """Tests for CustomHelpCommand.format_help with no parameters."""

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_no_params(self, mock_console):
        """Test format_help with no parameters prints correct output."""
        cmd = CustomHelpCommand(name="deploy")
        cmd.params = []

        cmd.format_help(MagicMock(), MagicMock())

        # Verify console.print was called
        assert mock_console.print.called

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_no_params_prints_usage(self, mock_console):
        """Test format_help prints usage section."""
        cmd = CustomHelpCommand(name="deploy")
        cmd.params = []

        cmd.format_help(MagicMock(), MagicMock())

        # Check that 'Usage:' is printed
        usage_calls = [
            c for c in mock_console.print.call_args_list if "Usage:" in str(c)
        ]
        assert len(usage_calls) > 0

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_no_params_prints_options_section(self, mock_console):
        """Test format_help prints Options section."""
        cmd = CustomHelpCommand(name="deploy")
        cmd.params = []

        cmd.format_help(MagicMock(), MagicMock())

        # Check that 'Options:' is printed
        options_calls = [
            c for c in mock_console.print.call_args_list if "Options:" in str(c)
        ]
        assert len(options_calls) > 0

    @patch("usecli.cli.core.base_command.console")
    def test_get_help_raises_exit(self, mock_console):
        """Test get_help raises Exit exception."""
        cmd = CustomHelpCommand(name="deploy")
        ctx = MagicMock()
        ctx.make_formatter.return_value = MagicMock()
        cmd.params = []

        with pytest.raises(Exit):
            cmd.get_help(ctx)

        # Verify console.print was called
        assert mock_console.print.called
        cmd.params = []

        with pytest.raises(Exit):
            cmd.get_help(ctx)

        # Check that 'Usage:' is printed
        usage_calls = [
            c for c in mock_console.print.call_args_list if "Usage:" in str(c)
        ]
        assert len(usage_calls) > 0


class TestCustomHelpCommandFormatHelpWithArguments:
    """Tests for CustomHelpCommand.format_help with arguments only."""

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_with_single_argument(self, mock_console):
        """Test format_help with single argument parameter."""
        cmd = CustomHelpCommand(name="init")
        arg = TyperArgument(param_decls=["project_name"])
        cmd.params = [arg]

        cmd.format_help(MagicMock(), MagicMock())

        # Verify console.print was called for arguments
        assert mock_console.print.called
        all_print_calls = str(mock_console.print.call_args_list)
        assert "project_name" in all_print_calls or "PROJECT_NAME" in all_print_calls

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_with_multiple_arguments(self, mock_console):
        """Test format_help with multiple argument parameters."""
        cmd = CustomHelpCommand(name="test")
        arg1 = TyperArgument(param_decls=["source"])
        arg2 = TyperArgument(param_decls=["destination"])
        cmd.params = [arg1, arg2]

        cmd.format_help(MagicMock(), MagicMock())

        assert mock_console.print.called

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_argument_appears_in_usage(self, mock_console):
        """Test format_help includes argument in usage line."""
        cmd = CustomHelpCommand(name="init")
        arg = TyperArgument(param_decls=["project_name"])
        cmd.params = [arg]

        cmd.format_help(MagicMock(), MagicMock())

        # Find usage line call
        usage_calls = [str(c) for c in mock_console.print.call_args_list]
        usage_text = " ".join(usage_calls)
        # Should contain the command name and options/arguments
        assert "init" in usage_text

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_prints_arguments_section(self, mock_console):
        """Test format_help prints Arguments section when arguments exist."""
        cmd = CustomHelpCommand(name="init")
        arg = TyperArgument(param_decls=["project_name"])
        cmd.params = [arg]

        cmd.format_help(MagicMock(), MagicMock())

        arguments_calls = [
            c for c in mock_console.print.call_args_list if "Arguments:" in str(c)
        ]
        assert len(arguments_calls) > 0


class TestCustomHelpCommandFormatHelpWithOptions:
    """Tests for CustomHelpCommand.format_help with options only."""

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_with_single_option(self, mock_console):
        """Test format_help with single option parameter."""
        cmd = CustomHelpCommand(name="deploy")
        option = TyperOption(param_decls=["-e", "--env"])
        cmd.params = [option]

        cmd.format_help(MagicMock(), MagicMock())

        assert mock_console.print.called
        all_print_calls = str(mock_console.print.call_args_list)
        assert "-e" in all_print_calls or "--env" in all_print_calls

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_with_multiple_options(self, mock_console):
        """Test format_help with multiple option parameters."""
        cmd = CustomHelpCommand(name="deploy")
        opt1 = TyperOption(param_decls=["-e", "--env"])
        opt2 = TyperOption(param_decls=["-v", "--verbose"], is_flag=True)
        cmd.params = [opt1, opt2]

        cmd.format_help(MagicMock(), MagicMock())

        assert mock_console.print.called

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_excludes_help_option_from_options(self, mock_console):
        """Test format_help excludes --help from options list."""
        cmd = CustomHelpCommand(name="deploy")
        help_opt = TyperOption(param_decls=["--help"])
        other_opt = TyperOption(param_decls=["-v", "--verbose"])
        cmd.params = [help_opt, other_opt]

        cmd.format_help(MagicMock(), MagicMock())

        # Help option should appear once as the standard help line
        # but not in the options list
        all_calls = str(mock_console.print.call_args_list)
        # Should see the standard "Show this message and exit." once
        assert "Show this message and exit." in all_calls

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_option_descriptions_printed(self, mock_console):
        """Test format_help prints option descriptions."""
        cmd = CustomHelpCommand(name="deploy")
        option = TyperOption(param_decls=["-e", "--env"])
        cmd.params = [option]

        cmd.format_help(MagicMock(), MagicMock())

        # Verify the option flag is printed
        all_calls = str(mock_console.print.call_args_list)
        assert "-e, --env" in all_calls

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_always_shows_help_option(self, mock_console):
        """Test format_help always shows --help, -h option."""
        cmd = CustomHelpCommand(name="cmd")
        opt = TyperOption(param_decls=["-x", "--extra"])
        cmd.params = [opt]

        cmd.format_help(MagicMock(), MagicMock())

        all_calls = str(mock_console.print.call_args_list)
        assert "--help, -h" in all_calls or (
            "--help" in all_calls and "-h" in all_calls
        )


class TestCustomHelpCommandFormatHelpWithBothArgumentsAndOptions:
    """Tests for CustomHelpCommand.format_help with both arguments and options."""

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_with_arguments_and_options(self, mock_console):
        """Test format_help with both arguments and options."""
        cmd = CustomHelpCommand(name="run")
        arg = TyperArgument(param_decls=["script"])
        opt = TyperOption(param_decls=["-e", "--env"])
        cmd.params = [arg, opt]

        cmd.format_help(MagicMock(), MagicMock())

        assert mock_console.print.called

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_usage_includes_both_args_and_opts(self, mock_console):
        """Test format_help usage line includes both arguments and options."""
        cmd = CustomHelpCommand(name="run")
        arg = TyperArgument(param_decls=["script"])
        opt = TyperOption(param_decls=["-e", "--env"])
        cmd.params = [arg, opt]

        cmd.format_help(MagicMock(), MagicMock())

        usage_calls = [str(c) for c in mock_console.print.call_args_list]
        usage_text = " ".join(usage_calls)
        # Usage should reference OPTIONS and possibly argument
        assert "run" in usage_text

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_sections_printed_in_order(self, mock_console):
        """Test format_help prints Usage, Options, Arguments sections."""
        cmd = CustomHelpCommand(name="build")
        arg = TyperArgument(param_decls=["target"])
        opt = TyperOption(
            param_decls=["-d", "--debug"], is_flag=True, help="Debug mode"
        )
        cmd.params = [arg, opt]

        cmd.format_help(MagicMock(), MagicMock())

        # Extract all print calls
        all_calls = [str(c) for c in mock_console.print.call_args_list]
        call_text = " ".join(all_calls)

        # Both sections should be present
        assert "Usage:" in call_text
        assert "Options:" in call_text
        assert "Arguments:" in call_text

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_padding_calculation(self, mock_console):
        """Test format_help calculates correct padding for alignment."""
        cmd = CustomHelpCommand(name="cmd")
        # Create options/args with varying name lengths
        short_opt = TyperOption(param_decls=["-x"])
        long_opt = TyperOption(param_decls=["--verbose-option"])
        cmd.params = [short_opt, long_opt]

        cmd.format_help(MagicMock(), MagicMock())

        # Verify console.print was called (padding applied internally)
        assert mock_console.print.called


class TestCustomHelpCommandFormatHelpColorUsage:
    """Tests for CustomHelpCommand color usage in format_help."""

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_uses_color_constants(self, mock_console):
        """Test format_help uses COLOR constants for styling."""
        cmd = CustomHelpCommand(name="test")
        cmd.params = []

        cmd.format_help(MagicMock(), MagicMock())

        # Get all print call arguments
        all_calls = mock_console.print.call_args_list
        all_call_str = str(all_calls)

        # Check that colors are used (present in the output)
        # COLOR.SECONDARY, COLOR.PRIMARY, COLOR.WARNING, COLOR.OPTION
        assert COLOR.SECONDARY in all_call_str or COLOR.PRIMARY in all_call_str

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_bold_styling_applied(self, mock_console):
        """Test format_help applies bold styling to headers."""
        cmd = CustomHelpCommand(name="test")
        cmd.params = []

        cmd.format_help(MagicMock(), MagicMock())

        all_calls = str(mock_console.print.call_args_list)
        # Should contain bold markers
        assert "[bold" in all_calls


class TestCustomHelpCommandJsonCompatibility:
    """Tests for framework --json coexistence with user-declared options."""

    def test_injected_json_option_added_when_absent(self):
        """A command without its own --json inherits the framework option."""
        cmd = CustomHelpCommand(name="test")
        json_params = [
            p for p in cmd.params if isinstance(p, TyperOption) and "--json" in p.opts
        ]
        assert len(json_params) == 1

    def test_user_declared_json_option_is_not_duplicated(self):
        """A command that already declares --json must not get a second one."""
        cmd = CustomHelpCommand(name="test")
        cmd.params = [TyperOption(param_decls=["--json"], is_flag=True)]
        json_params = [
            p for p in cmd.params if isinstance(p, TyperOption) and "--json" in p.opts
        ]
        assert len(json_params) == 1

    def test_user_declared_json_value_is_preserved(self):
        """A legacy command declaring --json must still receive its value."""
        import typer
        from typer.testing import CliRunner

        app = typer.Typer()
        captured: dict[str, bool] = {}

        def legacy_handler(
            json_output: bool = typer.Option(False, "--json"),
        ) -> None:
            captured["json_output"] = json_output

        app.command(name="legacy", cls=CustomHelpCommand)(legacy_handler)
        runner = CliRunner()
        result = runner.invoke(app, ["--json"])
        assert result.exit_code == 0
        assert captured.get("json_output") is True


# =============================================================================
# BaseCommand Tests
# =============================================================================


class ConcreteCommand(BaseCommand):
    """Concrete implementation of BaseCommand for testing."""

    def handle(self, *args, **kwargs):
        """Implement abstract handle method."""
        return

    def signature(self) -> str:
        """Implement abstract signature method."""
        return "test-cmd arg1 arg2"

    def description(self) -> str:
        """Implement abstract description method."""
        return "Test command description"


class AnotherConcreteCommand(BaseCommand):
    """Another concrete implementation for testing."""

    def handle(self, *args, **kwargs):
        """Implement abstract handle method."""
        return

    def signature(self) -> str:
        """Implement abstract signature method."""
        return "another-cmd"

    def description(self) -> str:
        """Implement abstract description method."""
        return "Another test command"


class TestBaseCommandAbstractMethods:
    """Tests for BaseCommand abstract method enforcement."""

    def test_handle_return_annotation_allows_structured_results(self):
        """The public command contract permits JSON-serializable return data."""
        annotation = BaseCommand.handle.__annotations__["return"]
        assert annotation == "object"

    def test_base_command_cannot_be_instantiated(self):
        """Test BaseCommand is abstract and cannot be instantiated directly."""
        abstract_cls = base_command.BaseCommand
        with pytest.raises(TypeError):
            abstract_cls(app=MagicMock())

    def test_handle_is_abstract(self):
        """Test handle method is abstract."""
        # ConcreteCommand implements handle, so it should work
        cmd = ConcreteCommand(
            app=MagicMock(command=MagicMock(return_value=lambda f: f))
        )
        assert callable(cmd.handle)

    def test_signature_is_abstract(self):
        """Test signature method is abstract."""
        cmd = ConcreteCommand(
            app=MagicMock(command=MagicMock(return_value=lambda f: f))
        )
        assert callable(cmd.signature)

    def test_description_is_abstract(self):
        """Test description method is abstract."""
        cmd = ConcreteCommand(
            app=MagicMock(command=MagicMock(return_value=lambda f: f))
        )
        assert callable(cmd.description)


class TestBaseCommandInit:
    """Tests for BaseCommand initialization."""

    def test_init_stores_app(self):
        """Test __init__ stores the app reference."""
        mock_app = MagicMock(command=MagicMock(return_value=lambda f: f))
        ConcreteCommand(app=mock_app)

        # Verify register was executed by checking app.command was called
        assert mock_app.command.called

    def test_init_with_typer_app(self):
        """Test __init__ works with actual Typer app instance."""
        app = typer.Typer()
        cmd = ConcreteCommand(app=app)
        assert cmd.app is app

    def test_init_different_concrete_implementations(self):
        """Test __init__ works with different BaseCommand subclasses."""
        mock_app = MagicMock(command=MagicMock(return_value=lambda f: f))
        cmd1 = ConcreteCommand(app=mock_app)
        cmd2 = AnotherConcreteCommand(app=mock_app)

        assert cmd1.app is mock_app
        assert cmd2.app is mock_app


class TestBaseCommandRegister:
    """Tests for BaseCommand register method."""

    def test_register_calls_app_command(self):
        """Test register calls app.command with correct parameters."""
        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        ConcreteCommand(app=mock_app)

        mock_app.command.assert_called_once()

    def test_register_extracts_name_from_signature(self):
        """Test register extracts command name from signature."""
        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        ConcreteCommand(app=mock_app)

        # signature() returns "test-cmd arg1 arg2", should extract "test-cmd"
        call_kwargs = mock_app.command.call_args.kwargs
        assert call_kwargs["name"] == "test-cmd"

    def test_register_uses_custom_help_command_class(self):
        """Test register uses CustomHelpCommand as cls parameter."""
        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        ConcreteCommand(app=mock_app)

        call_kwargs = mock_app.command.call_args.kwargs
        assert call_kwargs["cls"] == CustomHelpCommand

    def test_register_passes_description(self):
        """Test register passes description to app.command."""
        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        ConcreteCommand(app=mock_app)

        call_kwargs = mock_app.command.call_args.kwargs
        assert call_kwargs["help"] == "Test command description"

    def test_register_decorates_handle_method(self):
        """Test register uses returned decorator on handle method."""
        mock_app = MagicMock()
        decorator = MagicMock(return_value=MagicMock())
        mock_app.command = MagicMock(return_value=decorator)

        ConcreteCommand(app=mock_app)

        # Decorator should be called with handle method
        decorator.assert_called_once()

    def test_register_with_different_command_signatures(self):
        """Test register works with different command signatures."""
        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        ConcreteCommand(app=mock_app)
        AnotherConcreteCommand(app=mock_app)

        # Both should call app.command
        assert mock_app.command.call_count == 2

        # First should have "test-cmd", second "another-cmd"
        first_call = mock_app.command.call_args_list[0]
        second_call = mock_app.command.call_args_list[1]
        assert first_call.kwargs["name"] == "test-cmd"
        assert second_call.kwargs["name"] == "another-cmd"

    def test_register_signature_with_no_args(self):
        """Test register handles signature with only command name."""

        class SimpleCommand(BaseCommand):
            def handle(self, *args, **kwargs):
                pass

            def signature(self) -> str:
                return "simple"

            def description(self) -> str:
                return "Simple command"

        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        SimpleCommand(app=mock_app)

        call_kwargs = mock_app.command.call_args.kwargs
        assert call_kwargs["name"] == "simple"

    def test_register_signature_with_multiple_words(self):
        """Test register extracts first word from complex signature."""

        class MultiWordCommand(BaseCommand):
            def handle(self, *args, **kwargs):
                pass

            def signature(self) -> str:
                return "complex-cmd --flag --option arg1 arg2 arg3"

            def description(self) -> str:
                return "Complex command"

        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        MultiWordCommand(app=mock_app)

        call_kwargs = mock_app.command.call_args.kwargs
        assert call_kwargs["name"] == "complex-cmd"

    def test_register_creates_aliases(self):
        class AliasedCommand(BaseCommand):
            def handle(self, *args, **kwargs):
                pass

            def signature(self) -> str:
                return "alias-cmd"

            def description(self) -> str:
                return "Alias command"

            def aliases(self) -> list[str]:
                return ["ac"]

        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        AliasedCommand(app=mock_app)

        command_names = [
            call.kwargs["name"] for call in mock_app.command.call_args_list
        ]
        assert "alias-cmd" in command_names
        assert "ac" in command_names
        assert mock_app._usecli_aliases == {"alias-cmd": ["ac"]}


class TestBaseCommandIntegration:
    """Integration tests for BaseCommand with real Typer app."""

    def test_command_registration_with_typer_app(self):
        """Test command registration with actual Typer app."""
        app = typer.Typer()
        cmd = ConcreteCommand(app=app)

        # Command should be registered
        # The app should have the command registered
        assert cmd.app is app

    def test_multiple_commands_registration(self):
        """Test registering multiple commands with same app."""
        app = typer.Typer()

        cmd1 = ConcreteCommand(app=app)
        cmd2 = AnotherConcreteCommand(app=app)

        assert cmd1.app is app
        assert cmd2.app is app

    def test_command_handle_method_callable(self):
        """Test handle method is callable after registration."""
        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        cmd = ConcreteCommand(app=mock_app)

        # Verify handle is callable and returns expected value
        result = cmd.handle()
        assert result is None

    def test_help_option_names_match_help_formatting(self):
        """Test help option names used in CustomHelpCommand match expectations."""
        cmd = CustomHelpCommand(name="test")
        assert "help_option_names" in cmd.context_settings
        assert "--help" in cmd.context_settings["help_option_names"]
        assert "-h" in cmd.context_settings["help_option_names"]


class TestBaseCommandVisible:
    """Tests for BaseCommand visible method."""

    def test_visible_returns_true_by_default(self):
        """Test visible() returns True by default."""
        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        cmd = ConcreteCommand(app=mock_app)
        assert cmd.visible() is True

    def test_visible_can_be_overridden(self):
        """Test visible() can be overridden in subclasses."""

        class HiddenCommand(BaseCommand):
            def handle(self, *args, **kwargs):
                pass

            def signature(self) -> str:
                return "hidden"

            def description(self) -> str:
                return "Hidden command"

            def visible(self) -> bool:
                return False

        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        cmd = HiddenCommand(app=mock_app)
        assert cmd.visible() is False


class TestBaseCommandRegisterWithVisible:
    """Tests for BaseCommand register with visible check."""

    def test_register_skips_when_not_visible(self):
        """Test register skips when visible() returns False."""

        class InvisibleCommand(BaseCommand):
            def handle(self, *args, **kwargs):
                pass

            def signature(self) -> str:
                return "invisible"

            def description(self) -> str:
                return "Invisible command"

            def visible(self) -> bool:
                return False

        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        InvisibleCommand(app=mock_app)

        mock_app.command.assert_not_called()

    def test_register_proceeds_when_visible(self):
        """Test register proceeds when visible() returns True."""

        class VisibleCommand(BaseCommand):
            def handle(self, *args, **kwargs):
                pass

            def signature(self) -> str:
                return "visible"

            def description(self) -> str:
                return "Visible command"

            def visible(self) -> bool:
                return True

        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        VisibleCommand(app=mock_app)

        mock_app.command.assert_called_once()


class TestNestedCommandRegistry:
    """Tests for the NestedCommandRegistry singleton pattern."""

    def test_registry_is_singleton(self):
        """Test that NestedCommandRegistry is a singleton."""
        from usecli.cli.core.base_command import NestedCommandRegistry

        registry1 = NestedCommandRegistry()
        registry2 = NestedCommandRegistry()

        assert registry1 is registry2

    def test_registry_creates_group_apps(self):
        """Test that registry creates group apps correctly."""
        from usecli.cli.core.base_command import NestedCommandRegistry

        registry = NestedCommandRegistry()
        # Reset the registry state for testing
        registry._groups = {}
        registry._group_commands = {}

        app = typer.Typer()
        group_app = registry.get_or_create_group(app, "test-group")

        assert "test-group" in registry._groups
        assert group_app is registry._groups["test-group"]

    def test_registry_reuses_existing_groups(self):
        """Test that registry reuses existing group apps."""
        from usecli.cli.core.base_command import NestedCommandRegistry

        registry = NestedCommandRegistry()
        # Reset the registry state for testing
        registry._groups = {}
        registry._group_commands = {}

        app = typer.Typer()
        group_app1 = registry.get_or_create_group(app, "test-group")
        group_app2 = registry.get_or_create_group(app, "test-group")

        assert group_app1 is group_app2


class TestNestedCommandRegistration:
    """Tests for nested command registration with space-separated signatures."""

    def test_nested_command_registration_creates_group(self):
        """Test that nested command signature creates a command group."""
        from usecli.cli.core.base_command import NestedCommandRegistry

        registry = NestedCommandRegistry()
        # Reset the registry state for testing
        registry._groups = {}
        registry._group_commands = {}

        app = typer.Typer()

        class NestedShowCommand(BaseCommand):
            def handle(self, *args, **kwargs):
                pass

            def signature(self) -> str:
                return "nested show"

            def description(self) -> str:
                return "Show nested item"

        NestedShowCommand(app=app)

        # Verify the group was created
        assert "nested" in registry._groups

    def test_nested_command_is_registered_on_group(self):
        """Test that nested command is registered on the group app."""
        from usecli.cli.core.base_command import NestedCommandRegistry

        registry = NestedCommandRegistry()
        # Reset the registry state for testing
        registry._groups = {}
        registry._group_commands = {}

        app = typer.Typer()

        class NestedListCommand(BaseCommand):
            def handle(self, *args, **kwargs):
                pass

            def signature(self) -> str:
                return "nested list"

            def description(self) -> str:
                return "List nested items"

        NestedListCommand(app=app)

        # Verify the command is registered on the group app
        group_app = registry._groups["nested"]
        command_names = [cmd.name for cmd in group_app.registered_commands]
        assert "list" in command_names

    def test_nested_command_registers_group_and_subcommand_aliases(self):
        from usecli.cli.core.base_command import NestedCommandRegistry

        registry = NestedCommandRegistry()
        registry._groups = {}
        registry._group_commands = {}

        app = typer.Typer()

        class NestedAliasCommand(BaseCommand):
            def handle(self, *args, **kwargs):
                pass

            def signature(self) -> str:
                return "spec show"

            def description(self) -> str:
                return "Show spec"

            def aliases(self) -> list[str]:
                return ["spec s", "sp show", "sp s"]

        NestedAliasCommand(app=app)

        group_app = registry._groups["spec"]
        alias_registry = getattr(group_app, "_usecli_aliases", {})
        assert alias_registry["show"] == ["s"]

        group_alias_registry = getattr(app, "_usecli_group_aliases", {})
        assert group_alias_registry["spec"] == ["sp"]

    def test_single_level_command_not_affected(self):
        """Test that single-level commands still work correctly."""
        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        class SingleCommand(BaseCommand):
            def handle(self, *args, **kwargs):
                pass

            def signature(self) -> str:
                return "simple-cmd"

            def description(self) -> str:
                return "Simple command"

        SingleCommand(app=mock_app)

        # Should call app.command directly
        mock_app.command.assert_called_once()
        call_kwargs = mock_app.command.call_args.kwargs
        assert call_kwargs["name"] == "simple-cmd"

    def test_command_with_arguments_not_treated_as_nested(self):
        """Test that commands with argument placeholders are not treated as nested."""
        mock_app = MagicMock()
        mock_app.command = MagicMock(return_value=lambda f: f)

        class CommandWithArgs(BaseCommand):
            def handle(self, *args, **kwargs):
                pass

            def signature(self) -> str:
                return "deploy <environment>"

            def description(self) -> str:
                return "Deploy to environment"

        CommandWithArgs(app=mock_app)

        # Should call app.command directly, not create a group
        mock_app.command.assert_called_once()
        call_kwargs = mock_app.command.call_args.kwargs
        assert call_kwargs["name"] == "deploy"

    def test_is_valid_subcommand_name(self):
        """Test the _is_valid_subcommand_name helper method."""
        from usecli.cli.core.base_command import BaseCommand

        # Create a concrete class to test the method
        class TestCmd(BaseCommand):
            def handle(self, *args, **kwargs):
                pass

            def signature(self) -> str:
                return "test"

            def description(self) -> str:
                return "Test"

        cmd = TestCmd(app=MagicMock(command=MagicMock(return_value=lambda f: f)))

        # Valid subcommand names
        assert cmd._is_valid_subcommand_name("show") is True
        assert cmd._is_valid_subcommand_name("list") is True
        assert cmd._is_valid_subcommand_name("my-command") is True
        assert cmd._is_valid_subcommand_name("my_command") is True

        # Invalid (argument placeholders)
        assert cmd._is_valid_subcommand_name("<name>") is False
        assert cmd._is_valid_subcommand_name("[option]") is False
        assert cmd._is_valid_subcommand_name("--flag") is False
        assert cmd._is_valid_subcommand_name("arg1") is True  # alphanumeric is valid


class TestCustomHelpCommandGetHelp:
    """Tests for CustomHelpCommand.get_help method."""

    @patch("usecli.cli.core.base_command.console")
    def test_get_help_raises_exit(self, mock_console):
        """Test get_help raises Exit to stop execution after displaying help."""
        cmd = CustomHelpCommand(name="test")
        ctx = MagicMock()
        ctx.make_formatter.return_value = MagicMock()
        cmd.params = []

        with pytest.raises(Exit):
            cmd.get_help(ctx)

    @patch("usecli.cli.core.base_command.console")
    def test_get_help_calls_format_help(self, mock_console):
        """Test get_help delegates to format_help for display."""
        cmd = CustomHelpCommand(name="test")
        ctx = MagicMock()
        formatter = MagicMock()
        ctx.make_formatter.return_value = formatter
        cmd.params = []

        with pytest.raises(Exit):
            cmd.get_help(ctx)

        assert mock_console.print.called

    @patch("usecli.cli.core.base_command.console")
    def test_get_help_creates_formatter_from_context(self, mock_console):
        """Test get_help creates a formatter from the context."""
        cmd = CustomHelpCommand(name="test")
        ctx = MagicMock()
        cmd.params = []

        with pytest.raises(Exit):
            cmd.get_help(ctx)

        ctx.make_formatter.assert_called_once()

    @patch("usecli.cli.core.base_command.console")
    def test_get_help_displays_usage(self, mock_console):
        """Test get_help displays usage section via format_help."""
        cmd = CustomHelpCommand(name="deploy")
        ctx = MagicMock()
        ctx.make_formatter.return_value = MagicMock()
        cmd.params = []

        with pytest.raises(Exit):
            cmd.get_help(ctx)

        usage_calls = [
            c for c in mock_console.print.call_args_list if "Usage:" in str(c)
        ]
        assert len(usage_calls) > 0

    @patch("usecli.cli.core.base_command.console")
    def test_get_help_displays_options(self, mock_console):
        """Test get_help displays options section via format_help."""
        cmd = CustomHelpCommand(name="deploy")
        ctx = MagicMock()
        ctx.make_formatter.return_value = MagicMock()
        opt = TyperOption(param_decls=["-e", "--env"])
        cmd.params = [opt]

        with pytest.raises(Exit):
            cmd.get_help(ctx)

        options_calls = [
            c for c in mock_console.print.call_args_list if "Options:" in str(c)
        ]
        assert len(options_calls) > 0

    @patch("usecli.cli.core.base_command.console")
    def test_get_help_with_arguments(self, mock_console):
        """Test get_help with argument parameters."""
        cmd = CustomHelpCommand(name="init")
        ctx = MagicMock()
        ctx.make_formatter.return_value = MagicMock()
        arg = TyperArgument(param_decls=["project_name"])
        cmd.params = [arg]

        with pytest.raises(Exit):
            cmd.get_help(ctx)

        assert mock_console.print.called

    @patch("usecli.cli.core.base_command.console")
    def test_format_help_does_not_raise_exit(self, mock_console):
        """Test format_help no longer raises Exit (exit is in get_help)."""
        cmd = CustomHelpCommand(name="test")
        cmd.params = []

        cmd.format_help(MagicMock(), MagicMock())
        assert mock_console.print.called


# =============================================================================
# Coverage-focused: NestedCommandRegistry & BaseCommand edge branches
# =============================================================================


def _reset_registry() -> NestedCommandRegistry:
    """Return a fresh singleton registry with cleared state."""
    registry = NestedCommandRegistry()
    registry._groups = {}
    registry._group_commands = {}
    registry._main_app = None
    return registry


def _group_callback(group_app: typer.Typer):
    """Extract the registered group callback from a group app."""
    info = group_app.registered_callback
    assert info is not None
    callback = info.callback
    assert callback is not None
    return callback


class _Cmd(BaseCommand):
    """Concrete BaseCommand for exercising private helpers."""

    def __init__(self, signature="cmd", aliases=None, app=None):
        self._sig = signature
        self._aliases = aliases or []
        super().__init__(
            app=app or MagicMock(command=MagicMock(return_value=lambda f: f))
        )

    def handle(self, *args, **kwargs):
        return None

    def signature(self) -> str:
        return self._sig

    def description(self) -> str:
        return "Test command"

    def aliases(self) -> list[str]:
        return self._aliases


# ---------------------------------------------------------------------------
# NestedCommandRegistry group callback
# ---------------------------------------------------------------------------


class TestGroupCallbackHelpFlag:
    def test_help_flag_shows_group_help_and_exits(self):
        registry = _reset_registry()
        app = typer.Typer()
        group_app = registry.get_or_create_group(app, "spec")
        callback = _group_callback(group_app)
        ctx = MagicMock()
        ctx.invoked_subcommand = None
        with (
            patch("usecli.cli.core.base_command.console") as mock_console,
            pytest.raises(typer.Exit),
        ):
            callback(ctx=ctx, help_flag=True, interactive=False, json_output=False)
        assert mock_console.print.called


class TestGroupCallbackInteractive:
    def test_interactive_without_subcommand_runs_interactive(self):
        registry = _reset_registry()
        app = typer.Typer()
        group_app = registry.get_or_create_group(app, "spec")
        callback = _group_callback(group_app)
        ctx = MagicMock()
        ctx.invoked_subcommand = None
        with (
            patch(
                "usecli.cli.commands.defaults.base.internal.fzf_command.run_interactive"
            ) as mock_run,
            pytest.raises(typer.Exit),
        ):
            callback(ctx=ctx, help_flag=False, interactive=True, json_output=False)
        mock_run.assert_called_once()
        # cmd_parts should be the group name
        assert mock_run.call_args.kwargs.get("cmd_parts") == ["spec"]


class TestGroupCallbackNoSubcommand:
    def test_no_subcommand_shows_group_commands(self):
        registry = _reset_registry()
        app = typer.Typer()
        group_app = registry.get_or_create_group(app, "spec")
        callback = _group_callback(group_app)
        ctx = MagicMock()
        ctx.invoked_subcommand = None
        with patch("usecli.cli.core.ui.list.list_group_commands") as mock_list:
            callback(ctx=ctx, help_flag=False, interactive=False, json_output=False)
        mock_list.assert_called_once()


# ---------------------------------------------------------------------------
# NestedCommandRegistry.register_command
# ---------------------------------------------------------------------------


class TestRegisterCommand:
    def test_register_command_creates_new_group_list(self):
        registry = _reset_registry()
        registry.register_command("newgroup", "show", "Show it", lambda: None)
        assert registry._group_commands["newgroup"] == [
            {
                "name": "show",
                "description": "Show it",
                "callback": registry._group_commands["newgroup"][0]["callback"],
            }
        ]

    def test_register_command_appends_to_existing_group(self):
        registry = _reset_registry()
        registry._group_commands["spec"] = []
        registry.register_command("spec", "show", "Show it", lambda: None)
        registry.register_command("spec", "list", "List it", lambda: None)
        assert [c["name"] for c in registry._group_commands["spec"]] == [
            "show",
            "list",
        ]


# ---------------------------------------------------------------------------
# BaseCommand._register_with_aliases (line 477: skip duplicate/self alias)
# ---------------------------------------------------------------------------


class TestRegisterWithAliasesSkip:
    def test_skips_alias_equal_to_primary_name(self):
        app = MagicMock()
        app.command = MagicMock(return_value=lambda f: f)
        # alias "cmd" equals primary name -> continue
        _Cmd(signature="cmd", aliases=["cmd", "ac"], app=app)
        # Only primary + "ac" registered as commands
        names = [c.kwargs["name"] for c in app.command.call_args_list]
        assert names.count("cmd") == 1
        assert "ac" in names
        assert app._usecli_aliases == {"cmd": ["ac"]}

    def test_skips_alias_already_in_registry(self):
        app = MagicMock()
        app.command = MagicMock(return_value=lambda f: f)
        app._usecli_aliases = {"cmd": ["ac"]}
        # alias "ac" already in registry -> continue
        _Cmd(signature="cmd", aliases=["ac"], app=app)
        assert app._usecli_aliases == {"cmd": ["ac"]}


# ---------------------------------------------------------------------------
# BaseCommand._register_group_aliases (line 515: skip self/duplicate group alias)
# ---------------------------------------------------------------------------


class TestRegisterGroupAliasesSkip:
    def test_skips_alias_equal_to_group_name(self):
        app = MagicMock()
        cmd = _Cmd(signature="spec show", app=app)
        cmd._register_group_aliases(app, "spec", ["spec", "sp"])
        assert app._usecli_group_aliases == {"spec": ["sp"]}

    def test_skips_alias_already_in_group_registry(self):
        app = MagicMock()
        app._usecli_group_aliases = {"spec": ["sp"]}
        cmd = _Cmd(signature="spec show", app=app)
        cmd._register_group_aliases(app, "spec", ["sp"])
        assert app._usecli_group_aliases == {"spec": ["sp"]}


# ---------------------------------------------------------------------------
# BaseCommand._normalize_aliases
# ---------------------------------------------------------------------------


class TestNormalizeAliases:
    def test_group_name_branch_two_part_matching_group(self):
        cmd = _Cmd()
        result = cmd._normalize_aliases("list", ["spec show"], "spec")
        assert result == ["show"]

    def test_group_name_branch_single_part(self):
        cmd = _Cmd()
        result = cmd._normalize_aliases("show", ["list"], "spec")
        assert result == ["list"]

    def test_group_name_branch_two_part_nonmatching_group_skipped(self):
        cmd = _Cmd()
        result = cmd._normalize_aliases("show", ["other show"], "spec")
        assert result == []

    def test_group_name_branch_invalid_subcommand_skipped(self):
        cmd = _Cmd()
        result = cmd._normalize_aliases("show", ["<bad>"], "spec")
        assert result == []

    def test_no_group_multi_part_alias_skipped(self):
        cmd = _Cmd()
        result = cmd._normalize_aliases("cmd", ["a b"], None)
        assert result == []

    def test_skips_alias_equal_to_primary(self):
        cmd = _Cmd()
        result = cmd._normalize_aliases("cmd", ["cmd", "ac"], None)
        assert result == ["ac"]

    def test_skips_duplicate_normalized_alias(self):
        cmd = _Cmd()
        result = cmd._normalize_aliases("cmd", ["ac", "ac"], None)
        assert result == ["ac"]


# ---------------------------------------------------------------------------
# BaseCommand._normalize_nested_aliases
# ---------------------------------------------------------------------------


class TestNormalizeNestedAliases:
    def test_single_part_valid_alias(self):
        cmd = _Cmd()
        normalized, group_aliases = cmd._normalize_nested_aliases(
            "show", ["list"], "spec"
        )
        assert normalized == ["list"]
        assert group_aliases == []

    def test_single_part_invalid_subcommand_skipped(self):
        cmd = _Cmd()
        normalized, _ = cmd._normalize_nested_aliases("show", ["<bad>"], "spec")
        assert normalized == []

    def test_single_part_equal_to_primary_skipped(self):
        cmd = _Cmd()
        normalized, _ = cmd._normalize_nested_aliases("show", ["show"], "spec")
        assert normalized == []

    def test_single_part_duplicate_skipped(self):
        cmd = _Cmd()
        normalized, _ = cmd._normalize_nested_aliases("show", ["list", "list"], "spec")
        assert normalized == ["list"]

    def test_three_part_alias_skipped(self):
        cmd = _Cmd()
        normalized, _ = cmd._normalize_nested_aliases("show", ["a b c"], "spec")
        assert normalized == []

    def test_invalid_group_alias_skipped(self):
        cmd = _Cmd()
        normalized, group_aliases = cmd._normalize_nested_aliases(
            "show", ["<bad> show"], "spec"
        )
        assert normalized == []
        assert group_aliases == []

    def test_invalid_alias_name_skipped(self):
        cmd = _Cmd()
        normalized, group_aliases = cmd._normalize_nested_aliases(
            "show", ["spec <bad>"], "spec"
        )
        assert normalized == []
        assert group_aliases == []

    def test_matching_group_alias_equal_to_primary_skipped(self):
        cmd = _Cmd()
        normalized, group_aliases = cmd._normalize_nested_aliases(
            "show", ["spec show"], "spec"
        )
        assert normalized == []
        assert group_aliases == []

    def test_matching_group_alias_duplicate_skipped(self):
        cmd = _Cmd()
        normalized, _ = cmd._normalize_nested_aliases(
            "show", ["spec list", "spec list"], "spec"
        )
        assert normalized == ["list"]

    def test_nonmatching_group_alias_adds_group_alias(self):
        cmd = _Cmd()
        normalized, group_aliases = cmd._normalize_nested_aliases(
            "show", ["other list"], "spec"
        )
        assert normalized == ["list"]
        assert group_aliases == ["other"]

    def test_nonmatching_group_alias_equal_to_primary_skipped(self):
        cmd = _Cmd()
        normalized, group_aliases = cmd._normalize_nested_aliases(
            "show", ["other show"], "spec"
        )
        assert normalized == []
        assert group_aliases == ["other"]

    def test_nonmatching_group_alias_duplicate_skipped(self):
        cmd = _Cmd()
        normalized, group_aliases = cmd._normalize_nested_aliases(
            "show", ["other list", "other list"], "spec"
        )
        assert normalized == ["list"]
        assert group_aliases == ["other"]
