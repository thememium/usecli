"""Tests for usecli.cli.commands.defaults.base.internal.interactive_command."""

from __future__ import annotations

import contextlib
import inspect
from unittest.mock import MagicMock, patch

import click
import pytest
import typer

from usecli.cli.commands.defaults.base.internal.interactive_command import (
    _build_preview,
    _fit,
    _get_optional_options,
    _get_required_arguments,
    _humanize_name,
    _menu_entry,
    _resolve_group_alias,
    _run_command_menu,
    _select_command,
    run_interactive,
)

_FZF = "usecli.cli.commands.defaults.base.internal.interactive_command"


def _cmd(name, help="", callback=None, **kwargs):
    c = MagicMock()
    c.name = name
    c.help = help
    c.callback = callback
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


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
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command_from_info"
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
# _run_command_menu
# ---------------------------------------------------------------------------


class TestRunCommandMenu:
    @patch(f"{_FZF}.terminal_menu", return_value=["hello\x1fhello"])
    @patch(f"{_FZF}.sys")
    def test_returns_selected_command_name(self, mock_sys, mock_menu):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        result = _run_command_menu(["hello\x1fhello"], title="usecli » commands")
        assert result == "hello"
        kwargs = mock_menu.call_args.kwargs
        assert kwargs["search"] is True
        assert kwargs["search_key"] == "/"
        assert kwargs["vim_search"] is True
        assert kwargs["title"] == "usecli » commands"
        assert "/ search" in kwargs["status_bar"]
        assert "ctrl-u clear" in kwargs["status_bar"]

    @patch(f"{_FZF}.terminal_menu", return_value=[])
    @patch(f"{_FZF}.sys")
    def test_returns_none_when_cancelled(self, mock_sys, mock_menu):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        assert _run_command_menu(["hello\x1fhello"], title="t") is None

    @patch(f"{_FZF}.terminal_menu")
    @patch(f"{_FZF}.sys")
    def test_requires_a_tty(self, mock_sys, mock_menu):
        mock_sys.stdin.isatty.return_value = False
        mock_sys.stdout.isatty.return_value = True
        from usecli.cli.core.exceptions import UsecliError

        with pytest.raises(UsecliError):
            _run_command_menu(["hello\x1fhello"], title="t")
        mock_menu.assert_not_called()

    @patch(f"{_FZF}.terminal_menu", return_value=["hello\x1fhello"])
    @patch(f"{_FZF}.sys")
    def test_passes_preview_callable(self, mock_sys, mock_menu):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        preview = MagicMock(return_value="help")
        _run_command_menu(["hello\x1fhello"], title="t", preview_command=preview)
        assert mock_menu.call_args.kwargs["preview_command"] is preview

    @patch(f"{_FZF}.terminal_menu")
    def test_returns_none_without_entries(self, mock_menu):
        assert _run_command_menu([], title="t") is None
        mock_menu.assert_not_called()


# ---------------------------------------------------------------------------
# _select_command and entry formatting
# ---------------------------------------------------------------------------


class TestSelectCommand:
    def test_builds_aligned_entries_with_fallbacks(self):
        app = MagicMock()
        commands = [
            {"name": "hello", "help": "Say hello"},
            {"name": "db:migrate", "help": ""},
        ]
        with patch(f"{_FZF}._run_command_menu", return_value="hello") as menu:
            result = _select_command(
                commands,
                app=app,
                script_name="usecli",
                title="usecli » select a command",
            )
        assert result == "hello"
        entries = menu.call_args.args[0]
        assert entries[0].endswith("\x1fhello")
        assert "Say hello" in entries[0]
        assert entries[1].endswith("\x1fdb:migrate")
        assert "Db migrate" in entries[1]

    def test_preview_is_built_lazily_and_cached(self):
        app = MagicMock()
        commands = [{"name": "hello", "help": "Say hello"}]
        with (
            patch(f"{_FZF}._run_command_menu") as menu,
            patch(f"{_FZF}._build_preview", return_value="preview") as build,
        ):
            _select_command(commands, app=app, script_name="usecli", title="t")
            preview = menu.call_args.kwargs["preview_command"]
            assert preview("hello") == "preview"
            assert preview("hello") == "preview"
        build.assert_called_once()

    def test_returns_none_without_commands(self):
        assert (
            _select_command([], app=MagicMock(), script_name="usecli", title="t")
            is None
        )

    def test_humanize_name(self):
        assert _humanize_name("db:migrate-all") == "Db migrate all"

    def test_fit_truncates(self):
        assert _fit("abcdef", 4) == "abc…"
        assert _fit("abc", 4) == "abc"

    def test_fit_handles_tiny_widths(self):
        assert _fit("abc", 0) == ""
        assert _fit("abc", 1) == "…"

    def test_menu_entry_escapes_preview_separator(self):
        entry = _menu_entry("cmd", "a | b", 4)
        assert "a \\| b" in entry
        assert entry.endswith("\x1fcmd")

    def test_menu_entry_without_description_is_just_the_name(self):
        assert _menu_entry("cmd", "", 8) == "cmd\x1fcmd"


class TestBuildPreview:
    def test_leaf_preview_includes_usage_args_and_options(self):
        entry = {"name": "hello", "help": "Say hello", "command": MagicMock()}
        with (
            patch(
                f"{_FZF}._get_required_arguments",
                return_value=[("name", "who to greet", str)],
            ),
            patch(
                f"{_FZF}._get_optional_options",
                return_value=[("loud", "--loud", "shout", bool)],
            ),
        ):
            text = _build_preview(entry, MagicMock(), "usecli")
        assert "Say hello" in text
        assert "Usage: usecli hello <name> [OPTIONS]" in text
        assert "who to greet" in text
        assert "--loud" in text
        assert "shout" in text

    def test_group_preview_lists_subcommands(self):
        entry = {"name": "db", "help": "Database commands", "is_group": True}
        subs = [{"name": "migrate", "help": "Run migrations"}]
        with patch(f"{_FZF}._get_group_subcommands", return_value=subs):
            text = _build_preview(entry, MagicMock(), "usecli")
        assert "Usage: usecli db <command>" in text
        assert "migrate" in text
        assert "Run migrations" in text


# ---------------------------------------------------------------------------
# run_interactive
# ---------------------------------------------------------------------------


class TestRunInteractive:
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value=None,
    )
    def test_returns_when_no_selection(self, mock_select):
        app = MagicMock()
        app.registered_commands = [_cmd("test", "Test")]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app)
        mock_select.assert_called_once()

    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value="test",
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command.subprocess.run"
    )
    def test_runs_selected_command(self, mock_run, mock_select):
        app = MagicMock()
        cmd = _cmd("test", "Test")
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
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
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value="test",
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command.subprocess.run"
    )
    def test_handles_extra_args(self, mock_run, mock_select):
        app = MagicMock()
        cmd = _cmd("test", "Test")
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app, extra_args=["--verbose"])
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "--verbose" in call_args

    def test_raises_on_unknown_command(self):
        app = MagicMock()
        cmd = _cmd("test", "Test")
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            with pytest.raises(typer.Exit):
                run_interactive(app, cmd_parts=["nonexistent"])

    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value="make:command",
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command.subprocess.run"
    )
    def test_handles_colon_commands(self, mock_run, mock_select):
        app = MagicMock()
        cmd = _cmd("make:command", "Make command")
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app)
        mock_run.assert_called_once()

    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value="test",
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command.subprocess.run"
    )
    def test_resolves_group_alias(self, mock_run, mock_select):
        app = MagicMock()
        app._usecli_group_aliases = {"test": ["t"]}
        cmd = _cmd("test", "Test command")
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            # First call returns "test" (the alias), second call returns "test" (the resolved)
            mock_select.side_effect = ["test", "test"]
            run_interactive(app)
        mock_run.assert_called_once()

    def test_raises_when_extra_args_on_non_group(self):
        app = MagicMock()
        app._usecli_group_aliases = {}
        cmd = _cmd("test", "Test")
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            with pytest.raises(typer.Exit):
                run_interactive(app, cmd_parts=["test", "extra"])

    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value="group",
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command.subprocess.run"
    )
    def test_handles_group_with_subcommands(self, mock_run, mock_select):
        app = MagicMock()
        app._usecli_group_aliases = {}
        sub_cmd = _cmd("sub", "Sub")
        group_cmd_entry = _cmd("group", "Group", is_group=True)
        app.registered_commands = [group_cmd_entry]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_group = MagicMock(spec=click.Group)
            mock_group.commands = {"group": MagicMock(spec=click.Group, help="Group")}
            mock_get_cmd.return_value = mock_group
            with patch(
                "usecli.cli.commands.defaults.base.internal.interactive_command._get_group_subcommands",
                return_value=[{"name": "sub", "help": "Sub", "command": sub_cmd}],
            ):
                run_interactive(app, cmd_parts=["group", "sub"])
        mock_run.assert_called_once()

    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value="group",
    )
    def test_returns_when_group_subcommand_cancelled(self, mock_select):
        app = MagicMock()
        app._usecli_group_aliases = {}
        sub_cmd = _cmd("sub", "Sub")
        group_cmd_entry = _cmd("group", "Group", is_group=True)
        app.registered_commands = [group_cmd_entry]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_group = MagicMock(spec=click.Group)
            mock_group.commands = {"group": MagicMock(spec=click.Group, help="Group")}
            mock_get_cmd.return_value = mock_group
            with patch(
                "usecli.cli.commands.defaults.base.internal.interactive_command._get_group_subcommands",
                return_value=[{"name": "sub", "help": "Sub", "command": sub_cmd}],
            ):
                mock_select.side_effect = ["group", None]
                run_interactive(app)

    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value="group",
    )
    def test_raises_when_group_has_no_subcommands(self, mock_select):
        app = MagicMock()
        app._usecli_group_aliases = {}
        group_cmd_entry = _cmd("group", "Group", is_group=True)
        app.registered_commands = [group_cmd_entry]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_group = MagicMock(spec=click.Group)
            mock_group.commands = {"group": MagicMock(spec=click.Group, help="Group")}
            mock_get_cmd.return_value = mock_group
            with (
                patch(
                    "usecli.cli.commands.defaults.base.internal.interactive_command._get_group_subcommands",
                    return_value=[],
                ),
                pytest.raises(typer.Exit),
            ):
                run_interactive(app, cmd_parts=["group"])

    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value="group",
    )
    def test_raises_when_unknown_group_subcommand(self, mock_select):
        app = MagicMock()
        app._usecli_group_aliases = {}
        sub_cmd = _cmd("sub", "Sub")
        group_cmd_entry = _cmd("group", "Group", is_group=True)
        app.registered_commands = [group_cmd_entry]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_group = MagicMock(spec=click.Group)
            mock_group.commands = {"group": MagicMock(spec=click.Group, help="Group")}
            mock_get_cmd.return_value = mock_group
            with (
                patch(
                    "usecli.cli.commands.defaults.base.internal.interactive_command._get_group_subcommands",
                    return_value=[{"name": "sub", "help": "Sub", "command": sub_cmd}],
                ),
                pytest.raises(typer.Exit),
            ):
                run_interactive(app, cmd_parts=["group", "nonexistent"])

    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value="test",
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command.subprocess.run"
    )
    def test_handles_no_callback_command(self, mock_run, mock_select):
        app = MagicMock()
        app._usecli_group_aliases = {}
        cmd = _cmd("test", "Test")
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app)
        mock_run.assert_called_once()

    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value="test",
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command.subprocess.run"
    )
    def test_builds_command_with_extra_args(self, mock_run, mock_select):
        app = MagicMock()
        app._usecli_group_aliases = {}
        cmd = _cmd("test", "Test")
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app, extra_args=["arg1", "arg2"])
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "arg1" in call_args
        assert "arg2" in call_args

    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value="test",
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command.subprocess.run"
    )
    def test_handles_selection(self, mock_run, mock_select):
        app = MagicMock()
        app._usecli_group_aliases = {}
        cmd = _cmd("test", "Test")
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app)
        mock_run.assert_called_once()


class TestGetGroupSubcommands:
    def test_returns_empty_when_no_group(self):
        from usecli.cli.commands.defaults.base.internal.interactive_command import (
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
        from usecli.cli.commands.defaults.base.internal.interactive_command import (
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
        from usecli.cli.commands.defaults.base.internal.interactive_command import (
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


# =============================================================================
# Coverage-focused: run_interactive and _get_required_arguments edge branches
# =============================================================================


class TestGetRequiredArgumentsHelpAttributeError:
    def test_swallows_attribute_error_for_help(self):
        """A required arg whose ``help`` property raises is handled (55-56)."""

        class _BadHelp:
            default = ...

            @property
            def help(self) -> str:
                raise AttributeError("no help")

        param = inspect.Parameter(
            "name",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            default=_BadHelp(),
            annotation=str,
        )
        cmd = MagicMock(callback=lambda: None)
        with patch(
            f"{_FZF}.inspect.signature", return_value=inspect.Signature([param])
        ):
            result = _get_required_arguments(cmd)
        assert result == [("name", "", str)]


def _make_app(commands):
    app = MagicMock()
    app.registered_commands = commands
    app._usecli_group_aliases = {}
    return app


def _mock_run():
    m = MagicMock()
    m.return_value = MagicMock(stdout="help text", stderr="", returncode=0)
    return m


def _patch_get_command(group_commands):
    mock_group = MagicMock(spec=click.Group)
    mock_group.commands = group_commands
    return patch(f"{_FZF}.typer.main.get_command", return_value=mock_group)


class TestRunInteractiveColonSections:
    def test_groups_and_sorts_colon_commands(self):
        app = _make_app([_cmd("db:migrate", "Migrate")])
        with (
            patch(f"{_FZF}._select_command", return_value="db:migrate"),
            patch(f"{_FZF}.subprocess.run", _mock_run()),
            _patch_get_command({}),
        ):
            run_interactive(app)


class TestRunInteractiveUnparseableSelection:
    def test_empty_cmd_name_raises(self):
        app = _make_app([_cmd("test", "Test")])
        with (
            patch(f"{_FZF}._select_command", return_value=""),
            _patch_get_command({}),
            pytest.raises(typer.Exit),
        ):
            run_interactive(app)


class TestRunInteractiveGroupAliasFromParts:
    def test_resolves_alias_when_provided_as_part(self):
        app = _make_app([_cmd("primary", "P")])
        app._usecli_group_aliases = {"primary": ["alias"]}
        with (
            patch(f"{_FZF}.subprocess.run", _mock_run()),
            _patch_get_command({}),
        ):
            run_interactive(app, cmd_parts=["alias"])


class TestRunInteractiveSubcommandFallback:
    def _group_app(self):
        app = _make_app([_cmd("group", "Group")])
        return app

    def test_subcommand_from_selection(self):
        app = self._group_app()
        sub_cmd = _cmd("sub", "Sub")
        with (
            patch(f"{_FZF}._select_command", return_value="sub"),
            patch(f"{_FZF}.subprocess.run", _mock_run()),
            _patch_get_command({"group": MagicMock(spec=click.Group, help="Group")}),
            patch(
                f"{_FZF}._get_group_subcommands",
                return_value=[{"name": "sub", "help": "Sub", "command": sub_cmd}],
            ),
        ):
            run_interactive(app, cmd_parts=["group"])

    def test_unparseable_subcommand_raises(self):
        app = self._group_app()
        sub_cmd = _cmd("sub", "Sub")
        with (
            patch(f"{_FZF}._select_command", return_value=""),
            _patch_get_command({"group": MagicMock(spec=click.Group, help="Group")}),
            patch(
                f"{_FZF}._get_group_subcommands",
                return_value=[{"name": "sub", "help": "Sub", "command": sub_cmd}],
            ),
            pytest.raises(typer.Exit),
        ):
            run_interactive(app, cmd_parts=["group"])


class TestRunInteractiveExtraArgsOnLeaf:
    def test_extra_args_on_non_group_raises(self):
        app = _make_app([_cmd("test", "T")])
        with (
            patch(f"{_FZF}.subprocess.run", _mock_run()),
            _patch_get_command({}),
            pytest.raises(typer.Exit),
        ):
            run_interactive(app, cmd_parts=["test", "extra"])


class TestRunInteractiveRequiredArgs:
    def _run(self, required, *, input_side_effect=None, confirm=True, int_value=3):
        cmd = _cmd("test", "T")
        app = _make_app([cmd])
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch(f"{_FZF}._get_required_arguments", return_value=required)
            )
            stack.enter_context(patch(f"{_FZF}._get_optional_options", return_value=[]))
            stack.enter_context(patch(f"{_FZF}.subprocess.run", _mock_run()))
            stack.enter_context(patch(f"{_FZF}.console"))
            stack.enter_context(patch(f"{_FZF}.Confirm.ask", return_value=confirm))
            stack.enter_context(patch(f"{_FZF}.IntPrompt.ask", return_value=int_value))
            stack.enter_context(_patch_get_command({}))
            if input_side_effect is not None:
                stack.enter_context(
                    patch("builtins.input", side_effect=input_side_effect)
                )
            run_interactive(app, cmd_parts=["test"])

    def test_string_argument(self):
        self._run([("name", "the name", str)], input_side_effect=["myvalue"])

    def test_string_argument_with_space_is_quoted(self):
        self._run([("name", "", str)], input_side_effect=["two words"])

    def test_string_argument_retries_after_empty(self):
        self._run([("name", "", str)], input_side_effect=["", "final"])

    def test_string_argument_eof_error(self):
        self._run([("name", "", str)], input_side_effect=[EOFError, "x"])

    def test_string_argument_keyboard_interrupt(self):
        with patch(f"{_FZF}._get_required_arguments", return_value=[("name", "", str)]):
            cmd = _cmd("test", "T")
            app = _make_app([cmd])
            with (
                patch(f"{_FZF}.subprocess.run", _mock_run()),
                patch(f"{_FZF}.console"),
                patch("builtins.input", side_effect=KeyboardInterrupt),
                _patch_get_command({}),
                pytest.raises(typer.Exit),
            ):
                run_interactive(app, cmd_parts=["test"])

    def test_bool_argument_enabled(self):
        self._run([("enabled", "", bool)], confirm=True)

    def test_bool_argument_disabled(self):
        self._run([("enabled", "", bool)], confirm=False)

    def test_int_argument(self):
        self._run([("count", "", int)], int_value=7)


class TestRunInteractiveOptionalFlags:
    def _run(self, opts, menu, *, input_side_effect=None, confirm=True, int_value=2):
        cmd = _cmd("test", "T")
        app = _make_app([cmd])
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                patch(f"{_FZF}._get_required_arguments", return_value=[])
            )
            stack.enter_context(
                patch(f"{_FZF}._get_optional_options", return_value=opts)
            )
            stack.enter_context(patch(f"{_FZF}.terminal_menu", return_value=menu))
            stack.enter_context(patch(f"{_FZF}.subprocess.run", _mock_run()))
            stack.enter_context(patch(f"{_FZF}.console"))
            stack.enter_context(patch(f"{_FZF}.Confirm.ask", return_value=confirm))
            stack.enter_context(patch(f"{_FZF}.IntPrompt.ask", return_value=int_value))
            stack.enter_context(_patch_get_command({}))
            if input_side_effect is not None:
                stack.enter_context(
                    patch("builtins.input", side_effect=input_side_effect)
                )
            run_interactive(app, cmd_parts=["test"])

    def test_no_options_selected(self):
        self._run([("verbose", "--verbose", "", bool)], [])

    def test_bool_option_enabled(self):
        self._run(
            [("verbose", "--verbose", "show detail", bool)],
            ["--verbose [bool] - show detail"],
        )

    def test_bool_option_disabled(self):
        self._run(
            [("verbose", "--verbose", "show detail", bool)],
            ["--verbose [bool] - show detail"],
            confirm=False,
        )

    def test_int_option(self):
        self._run([("count", "--count", "", int)], ["--count [int]"], int_value=5)

    def test_str_option(self):
        self._run(
            [("name", "--name", "", str)], ["--name"], input_side_effect=["hello"]
        )

    def test_str_option_with_help_text(self):
        self._run(
            [("name", "--name", "enter a name", str)],
            ["--name - enter a name"],
            input_side_effect=["hello"],
        )

    def test_str_option_with_space_is_quoted(self):
        self._run(
            [("name", "--name", "", str)], ["--name"], input_side_effect=["two words"]
        )

    def test_str_option_retries_after_empty(self):
        self._run(
            [("name", "--name", "", str)], ["--name"], input_side_effect=["", "hi"]
        )

    def test_str_option_keyboard_interrupt(self):
        with patch(
            f"{_FZF}._get_optional_options", return_value=[("name", "--name", "", str)]
        ):
            cmd = _cmd("test", "T")
            app = _make_app([cmd])
            with (
                patch(f"{_FZF}._get_required_arguments", return_value=[]),
                patch(f"{_FZF}.terminal_menu", return_value=["--name"]),
                patch(f"{_FZF}.subprocess.run", _mock_run()),
                patch(f"{_FZF}.console"),
                patch("builtins.input", side_effect=KeyboardInterrupt),
                _patch_get_command({}),
                pytest.raises(typer.Exit),
            ):
                run_interactive(app, cmd_parts=["test"])

    def test_required_and_optional_with_existing_extra(self):
        cmd = _cmd("test", "T")
        app = _make_app([cmd])
        with (
            patch(
                f"{_FZF}._get_required_arguments",
                return_value=[("name", "", str)],
            ),
            patch(
                f"{_FZF}._get_optional_options",
                return_value=[("verbose", "--verbose", "", bool)],
            ),
            patch(f"{_FZF}.terminal_menu", return_value=["--verbose [bool]"]),
            patch(f"{_FZF}.subprocess.run", _mock_run()),
            patch(f"{_FZF}.console"),
            patch(f"{_FZF}.Confirm.ask", return_value=True),
            patch("builtins.input", return_value="myvalue"),
            _patch_get_command({}),
        ):
            run_interactive(app, cmd_parts=["test"], extra_args=["--base"])
