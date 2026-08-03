"""Tests for usecli.cli.commands.defaults.base.internal.fzf_command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
import pytest
import typer

from usecli.cli.commands.defaults.base.internal.fzf_command import (
    FzfCommand,
    _get_optional_options,
    _get_required_arguments,
    _resolve_group_alias,
    _run_fzf_menu,
    run_interactive,
)

# ---------------------------------------------------------------------------
# _get_required_arguments
# ---------------------------------------------------------------------------


class TestGetRequiredArguments:
    def test_returns_empty_for_no_callback(self):
        cmd = MagicMock()
        cmd.callback = None
        assert _get_required_arguments(cmd) == []

    def test_returns_empty_for_no_params(self):
        def callback():
            pass

        cmd = MagicMock()
        cmd.callback = callback
        assert _get_required_arguments(cmd) == []

    def test_skips_self_parameter(self):
        class Cmd:
            def handle(self, name: str):
                pass

        cmd = MagicMock()
        cmd.callback = Cmd.handle
        result = _get_required_arguments(cmd)
        assert len(result) == 1
        assert result[0][0] == "name"

    def test_skips_optional_parameters(self):
        def callback(name: str, optional: str = "default"):
            pass

        cmd = MagicMock()
        cmd.callback = callback
        result = _get_required_arguments(cmd)
        assert len(result) == 1
        assert result[0][0] == "name"

    def test_handles_missing_annotation(self):
        def callback(name):
            pass

        cmd = MagicMock()
        cmd.callback = callback
        result = _get_required_arguments(cmd)
        assert len(result) == 1
        assert result[0][2] == str

    def test_handles_int_type(self):
        def callback(count: int):
            pass

        cmd = MagicMock()
        cmd.callback = callback
        result = _get_required_arguments(cmd)
        # Without typer.Argument(...), it won't be detected as required
        # because param.default is inspect.Parameter.empty
        assert len(result) == 1

    def test_handles_help_text_from_typer_argument(self):
        def callback(name: str = typer.Argument(..., help="Name arg")):
            pass

        cmd = MagicMock()
        cmd.callback = callback
        result = _get_required_arguments(cmd)
        assert len(result) == 1
        assert result[0][0] == "name"

    def test_handles_multiple_required_args(self):
        def callback(name: str, count: int):
            pass

        cmd = MagicMock()
        cmd.callback = callback
        result = _get_required_arguments(cmd)
        assert len(result) == 2

    def test_handles_no_annotation_with_typer_default(self):
        name_arg = typer.Argument(..., help="Name")

        def callback(name=name_arg):
            pass

        cmd = MagicMock()
        cmd.callback = callback
        result = _get_required_arguments(cmd)
        assert len(result) == 1
        assert result[0][2] == str


# ---------------------------------------------------------------------------
# _get_optional_options
# ---------------------------------------------------------------------------


class TestGetOptionalOptions:
    def test_returns_empty_for_none_command(self):
        assert _get_optional_options(None) == []  # type: ignore[ty:invalid-argument-type]

    def test_returns_empty_for_no_params(self):
        cmd = MagicMock(spec=click.Command)
        cmd.params = []
        assert _get_optional_options(cmd) == []

    def test_returns_options_from_click_command(self):
        opt = click.Option(["--verbose", "-v"], help="Verbose", is_flag=True)
        cmd = MagicMock(spec=click.Command)
        cmd.params = [opt]
        result = _get_optional_options(cmd)
        assert len(result) == 1
        assert result[0][0] == "verbose"
        assert "--verbose" in result[0][1]
        assert result[0][3] == bool

    def test_skips_help_option(self):
        opt = click.Option(["--help"], help="Show help")
        cmd = MagicMock(spec=click.Command)
        cmd.params = [opt]
        result = _get_optional_options(cmd)
        assert len(result) == 0

    def test_skips_interactive_option(self):
        opt = click.Option(["--interactive", "-i"], help="Interactive")
        cmd = MagicMock(spec=click.Command)
        cmd.params = [opt]
        result = _get_optional_options(cmd)
        assert len(result) == 0

    def test_skips_json_option(self):
        opt = click.Option(["--json"], help="JSON output")
        cmd = MagicMock(spec=click.Command)
        cmd.params = [opt]
        result = _get_optional_options(cmd)
        assert len(result) == 0

    def test_handles_int_option(self):
        opt = click.Option(["--count", "-c"], help="Count", type=int)
        cmd = MagicMock(spec=click.Command)
        cmd.params = [opt]
        result = _get_optional_options(cmd)
        assert len(result) == 1
        assert result[0][3] == int

    def test_handles_str_option(self):
        opt = click.Option(["--name", "-n"], help="Name")
        cmd = MagicMock(spec=click.Command)
        cmd.params = [opt]
        result = _get_optional_options(cmd)
        assert len(result) == 1
        assert result[0][3] == str

    def test_handles_bool_flag(self):
        opt = click.Option(["--debug"], help="Debug", is_flag=True)
        cmd = MagicMock(spec=click.Command)
        cmd.params = [opt]
        result = _get_optional_options(cmd)
        assert len(result) == 1
        assert result[0][3] == bool

    def test_handles_typer_command_info(self):
        opt = click.Option(["--verbose", "-v"], help="Verbose", is_flag=True)
        cmd = MagicMock(spec=typer.models.CommandInfo)
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command_from_info"
        ) as mock:
            mock.return_value = MagicMock(params=[opt])
            result = _get_optional_options(cmd)
            assert len(result) == 1

    def test_handles_non_click_non_typer_command(self):
        cmd = MagicMock()
        result = _get_optional_options(cmd)
        assert len(result) == 0

    def test_skips_non_option_params(self):
        arg = click.Argument(["name"])
        cmd = MagicMock(spec=click.Command)
        cmd.params = [arg]
        result = _get_optional_options(cmd)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# _resolve_group_alias
# ---------------------------------------------------------------------------


class TestResolveGroupAlias:
    def test_returns_name_when_no_registry(self):
        app = MagicMock(spec=[])
        assert _resolve_group_alias(app, "mygroup") == "mygroup"

    def test_returns_name_when_not_dict(self):
        app = MagicMock()
        app._usecli_group_aliases = "not a dict"
        assert _resolve_group_alias(app, "mygroup") == "mygroup"

    def test_returns_primary_when_exact_match(self):
        app = MagicMock()
        app._usecli_group_aliases = {"primary": ["alias1", "alias2"]}
        assert _resolve_group_alias(app, "primary") == "primary"

    def test_returns_primary_when_alias_match(self):
        app = MagicMock()
        app._usecli_group_aliases = {"primary": ["alias1", "alias2"]}
        assert _resolve_group_alias(app, "alias1") == "primary"

    def test_returns_name_when_no_match(self):
        app = MagicMock()
        app._usecli_group_aliases = {"primary": ["alias1"]}
        assert _resolve_group_alias(app, "other") == "other"

    def test_handles_empty_registry(self):
        app = MagicMock()
        app._usecli_group_aliases = {}
        assert _resolve_group_alias(app, "mygroup") == "mygroup"


# ---------------------------------------------------------------------------
# _run_fzf_menu
# ---------------------------------------------------------------------------


class TestRunFzfMenu:
    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command.terminal_menu",
        return_value=["option_a"],
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.sys")
    def test_falls_back_to_terminal_menu_when_not_tty(self, mock_sys, mock_menu):
        mock_sys.stdin.isatty.return_value = False
        mock_sys.stdout.isatty.return_value = True
        result = _run_fzf_menu(["option_a", "option_b"])
        assert result == "option_a"
        mock_menu.assert_called_once()

    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command.terminal_menu",
        return_value=[],
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.sys")
    def test_returns_none_when_terminal_menu_empty(self, mock_sys, mock_menu):
        mock_sys.stdin.isatty.return_value = False
        mock_sys.stdout.isatty.return_value = True
        result = _run_fzf_menu(["option_a"])
        assert result is None

    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command.shutil.which",
        return_value=None,
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command.terminal_menu",
        return_value=["option_a"],
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.sys")
    def test_falls_back_when_fzf_not_installed(self, mock_sys, mock_menu, mock_which):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        result = _run_fzf_menu(["option_a"])
        assert result == "option_a"

    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command.shutil.which",
        return_value="/usr/bin/fzf",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.sys")
    def test_returns_selection_from_fzf(self, mock_sys, mock_which, mock_run):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="selected_option\n")
        result = _run_fzf_menu(["option_a", "option_b"])
        assert result == "selected_option"

    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command.shutil.which",
        return_value="/usr/bin/fzf",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.sys")
    def test_returns_none_on_cancel(self, mock_sys, mock_which, mock_run):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        mock_run.return_value = MagicMock(returncode=130, stdout="")
        result = _run_fzf_menu(["option_a"])
        assert result is None

    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command.shutil.which",
        return_value="/usr/bin/fzf",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.sys")
    def test_returns_none_on_empty_output(self, mock_sys, mock_which, mock_run):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        result = _run_fzf_menu(["option_a"])
        assert result is None

    @patch("usecli.cli.core.error.handler.ErrorHandler.display_error")
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command.shutil.which",
        return_value="/usr/bin/fzf",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.sys")
    def test_raises_on_fzf_error(
        self, mock_sys, mock_which, mock_run, mock_display_error
    ):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        # Must have non-empty stdout to avoid early return
        mock_run.return_value = MagicMock(
            returncode=1, stdout="something", stderr="error"
        )
        with pytest.raises(typer.Exit):
            _run_fzf_menu(["option_a"])

    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command.shutil.which",
        return_value="/usr/bin/fzf",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.sys")
    def test_raises_on_file_not_found(self, mock_sys, mock_which, mock_run):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        mock_run.side_effect = FileNotFoundError
        from usecli.cli.core.exceptions import UsecliError

        with pytest.raises(UsecliError):
            _run_fzf_menu(["option_a"])

    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command.shutil.which",
        return_value="/usr/bin/fzf",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.sys")
    def test_passes_custom_prompt(self, mock_sys, mock_which, mock_run):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        mock_run.return_value = MagicMock(returncode=0, stdout="selected\n")
        _run_fzf_menu(["option_a"], prompt="custom » ")
        call_args = mock_run.call_args[0][0]
        assert any("custom » " in arg for arg in call_args)


# ---------------------------------------------------------------------------
# FzfCommand
# ---------------------------------------------------------------------------


class TestFzfCommand:
    def test_signature(self):
        app = MagicMock()
        cmd = FzfCommand(app)
        assert cmd.signature() == "fzf"

    def test_description(self):
        app = MagicMock()
        cmd = FzfCommand(app)
        assert (
            "finder" in cmd.description().lower() or "fzf" in cmd.description().lower()
        )

    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.run_interactive")
    def test_handle_calls_run_interactive(self, mock_run):
        app = MagicMock()
        cmd = FzfCommand(app)
        cmd.handle(extra_args=["--verbose"])
        mock_run.assert_called_once_with(app, extra_args=["--verbose"])


# ---------------------------------------------------------------------------
# run_interactive
# ---------------------------------------------------------------------------


class TestRunInteractive:
    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command._run_fzf_menu",
        return_value=None,
    )
    def test_returns_when_no_selection(self, mock_fzf):
        app = MagicMock()
        app.registered_commands = [MagicMock(name="test", help="Test")]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app)
        mock_fzf.assert_called_once()

    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command._run_fzf_menu",
        return_value="test",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    def test_runs_selected_command(self, mock_run, mock_fzf):
        app = MagicMock()
        cmd = MagicMock(name="test", help="Test", callback=None)
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app)
        mock_run.assert_called_once()

    def test_raises_when_no_commands(self):
        app = MagicMock()
        app.registered_commands = []
        with pytest.raises(typer.Exit):
            run_interactive(app)

    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command._run_fzf_menu",
        return_value="test",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    def test_handles_extra_args(self, mock_run, mock_fzf):
        app = MagicMock()
        cmd = MagicMock(name="test", help="Test", callback=None)
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app, extra_args=["--verbose"])
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "--verbose" in call_args

    def test_raises_on_unknown_command(self):
        app = MagicMock()
        cmd = MagicMock(name="test", help="Test", callback=None)
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            with pytest.raises(typer.Exit):
                run_interactive(app, cmd_parts=["nonexistent"])

    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command._run_fzf_menu",
        return_value="test",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    def test_handles_colon_commands(self, mock_run, mock_fzf):
        app = MagicMock()
        cmd = MagicMock(name="make:command", help="Make command", callback=None)
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app)
        mock_run.assert_called_once()

    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command._run_fzf_menu",
        return_value="test",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    def test_resolves_group_alias(self, mock_run, mock_fzf):
        app = MagicMock()
        app._usecli_group_aliases = {"test": ["t"]}
        cmd = MagicMock(name="test", help="Test command", callback=None)
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            # First call returns "test" (the alias), second call returns "test" (the resolved)
            mock_fzf.side_effect = ["test", "test"]
            run_interactive(app)
        mock_run.assert_called_once()

    def test_raises_when_extra_args_on_non_group(self):
        app = MagicMock()
        app._usecli_group_aliases = {}
        cmd = MagicMock(name="test", help="Test", callback=None)
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            with pytest.raises(typer.Exit):
                run_interactive(app, cmd_parts=["test", "extra"])

    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command._run_fzf_menu",
        return_value="group",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    def test_handles_group_with_subcommands(self, mock_run, mock_fzf):
        app = MagicMock()
        app._usecli_group_aliases = {}
        sub_cmd = MagicMock(name="sub", help="Sub", callback=None)
        group_cmd_entry = MagicMock(name="group", help="Group", is_group=True)
        app.registered_commands = [group_cmd_entry]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_group = MagicMock(spec=click.Group)
            mock_group.commands = {"group": MagicMock(spec=click.Group, help="Group")}
            mock_get_cmd.return_value = mock_group
            with patch(
                "usecli.cli.commands.defaults.base.internal.fzf_command._get_group_subcommands",
                return_value=[{"name": "sub", "help": "Sub", "command": sub_cmd}],
            ):
                run_interactive(app, cmd_parts=["group", "sub"])
        mock_run.assert_called_once()

    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command._run_fzf_menu",
        return_value="group",
    )
    def test_returns_when_group_subcommand_cancelled(self, mock_fzf):
        app = MagicMock()
        app._usecli_group_aliases = {}
        sub_cmd = MagicMock(name="sub", help="Sub", callback=None)
        group_cmd_entry = MagicMock(name="group", help="Group", is_group=True)
        app.registered_commands = [group_cmd_entry]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_group = MagicMock(spec=click.Group)
            mock_group.commands = {"group": MagicMock(spec=click.Group, help="Group")}
            mock_get_cmd.return_value = mock_group
            with patch(
                "usecli.cli.commands.defaults.base.internal.fzf_command._get_group_subcommands",
                return_value=[{"name": "sub", "help": "Sub", "command": sub_cmd}],
            ):
                mock_fzf.side_effect = ["group", None]
                run_interactive(app)

    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command._run_fzf_menu",
        return_value="group",
    )
    def test_raises_when_group_has_no_subcommands(self, mock_fzf):
        app = MagicMock()
        app._usecli_group_aliases = {}
        group_cmd_entry = MagicMock(name="group", help="Group", is_group=True)
        app.registered_commands = [group_cmd_entry]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_group = MagicMock(spec=click.Group)
            mock_group.commands = {"group": MagicMock(spec=click.Group, help="Group")}
            mock_get_cmd.return_value = mock_group
            with (
                patch(
                    "usecli.cli.commands.defaults.base.internal.fzf_command._get_group_subcommands",
                    return_value=[],
                ),
                pytest.raises(typer.Exit),
            ):
                run_interactive(app, cmd_parts=["group"])

    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command._run_fzf_menu",
        return_value="group",
    )
    def test_raises_when_unknown_group_subcommand(self, mock_fzf):
        app = MagicMock()
        app._usecli_group_aliases = {}
        sub_cmd = MagicMock(name="sub", help="Sub", callback=None)
        group_cmd_entry = MagicMock(name="group", help="Group", is_group=True)
        app.registered_commands = [group_cmd_entry]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_group = MagicMock(spec=click.Group)
            mock_group.commands = {"group": MagicMock(spec=click.Group, help="Group")}
            mock_get_cmd.return_value = mock_group
            with (
                patch(
                    "usecli.cli.commands.defaults.base.internal.fzf_command._get_group_subcommands",
                    return_value=[{"name": "sub", "help": "Sub", "command": sub_cmd}],
                ),
                pytest.raises(typer.Exit),
            ):
                run_interactive(app, cmd_parts=["group", "nonexistent"])

    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command._run_fzf_menu",
        return_value="test",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    def test_handles_no_callback_command(self, mock_run, mock_fzf):
        app = MagicMock()
        app._usecli_group_aliases = {}
        cmd = MagicMock(name="test", help="Test", callback=None)
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app)
        mock_run.assert_called_once()

    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command._run_fzf_menu",
        return_value="test",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    def test_builds_command_with_extra_args(self, mock_run, mock_fzf):
        app = MagicMock()
        app._usecli_group_aliases = {}
        cmd = MagicMock(name="test", help="Test", callback=None)
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app, extra_args=["arg1", "arg2"])
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "arg1" in call_args
        assert "arg2" in call_args

    @patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command._run_fzf_menu",
        return_value="test",
    )
    @patch("usecli.cli.commands.defaults.base.internal.fzf_command.subprocess.run")
    def test_handles_fzf_selection_with_extra_whitespace(self, mock_run, mock_fzf):
        app = MagicMock()
        app._usecli_group_aliases = {}
        cmd = MagicMock(name="test", help="Test", callback=None)
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app)
        mock_run.assert_called_once()


class TestGetGroupSubcommands:
    def test_returns_empty_when_no_group(self):
        from usecli.cli.commands.defaults.base.internal.fzf_command import (
            _get_group_subcommands,
        )

        app = MagicMock()
        app._usecli_group_aliases = {}
        with patch(
            "usecli.cli.core.base_command.NestedCommandRegistry"
        ) as mock_registry:
            mock_registry.return_value._groups = {}
            result = _get_group_subcommands(app, "nonexistent")
            assert result == []

    def test_returns_subcommands(self):
        from usecli.cli.commands.defaults.base.internal.fzf_command import (
            _get_group_subcommands,
        )

        app = MagicMock()
        app._usecli_group_aliases = {}
        sub_cmd = MagicMock()
        sub_cmd.name = "sub"
        sub_cmd.help = "Sub command"
        with patch(
            "usecli.cli.core.base_command.NestedCommandRegistry"
        ) as mock_registry:
            mock_group = MagicMock()
            mock_group.registered_commands = [sub_cmd]
            mock_registry.return_value._groups = {"group": mock_group}
            result = _get_group_subcommands(app, "group")
            assert len(result) == 1
            assert result[0]["name"] == "sub"

    def test_resolves_alias(self):
        from usecli.cli.commands.defaults.base.internal.fzf_command import (
            _get_group_subcommands,
        )

        app = MagicMock()
        app._usecli_group_aliases = {"group": ["alias"]}
        sub_cmd = MagicMock()
        sub_cmd.name = "sub"
        sub_cmd.help = "Sub command"
        with patch(
            "usecli.cli.core.base_command.NestedCommandRegistry"
        ) as mock_registry:
            mock_group = MagicMock()
            mock_group.registered_commands = [sub_cmd]
            mock_registry.return_value._groups = {"group": mock_group}
            result = _get_group_subcommands(app, "alias")
            assert len(result) == 1
