"""Tests for usecli.cli.commands.defaults.base.internal.interactive_command."""

from __future__ import annotations

import contextlib
import inspect
import os
import termios
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import click
import pytest
import typer

from usecli.cli.commands.defaults.base.internal.interactive_command import (
    _fit,
    _get_optional_options,
    _get_required_arguments,
    _humanize_name,
    _menu_entry,
    _open_tty_fd,
    _resolve_group_alias,
    _run_command_menu,
    _select_command,
    _type_into_terminal,
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
    @patch(f"{_FZF}.terminal_menu", return_value=["hello  Say hello"])
    @patch(f"{_FZF}.sys")
    def test_returns_selected_entry(self, mock_sys, mock_menu):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        result = _run_command_menu(["hello  Say hello"], title="usecli » commands")
        assert result == ("hello  Say hello", False)
        kwargs = mock_menu.call_args.kwargs
        assert kwargs["search"] is True
        assert kwargs["search_key"] == "/"
        assert kwargs["vim_search"] is True
        assert kwargs["title"] == "usecli » commands"
        assert kwargs["accept_keys"] == ("enter", "tab")
        assert "/ search" in kwargs["status_bar"]
        assert "ctrl-u clear" in kwargs["status_bar"]
        assert "tab insert" in kwargs["status_bar"]
        assert "preview_command" not in kwargs
        from usecli.cli.config.colors import COLOR

        assert kwargs["title_style"] == COLOR.ANSI.SECONDARY
        assert kwargs["entry_renderer"] is None

    @patch(f"{_FZF}.terminal_menu")
    @patch(f"{_FZF}.sys")
    def test_tab_accept_reports_print_only(self, mock_sys, mock_menu):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True

        class _Tabbed(list):
            accept_key = "tab"

        mock_menu.return_value = _Tabbed(["hello"])
        assert _run_command_menu(["hello"], title="t") == ("hello", True)

    @patch(f"{_FZF}.terminal_menu")
    @patch(f"{_FZF}.sys")
    def test_enter_accept_does_not_print(self, mock_sys, mock_menu):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True

        class _Entered(list):
            accept_key = "enter"

        mock_menu.return_value = _Entered(["hello"])
        assert _run_command_menu(["hello"], title="t") == ("hello", False)

    @patch(f"{_FZF}.terminal_menu", return_value=["hello"])
    @patch(f"{_FZF}.sys")
    def test_passes_entry_renderer(self, mock_sys, mock_menu):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        renderer = MagicMock(return_value="styled")
        _run_command_menu(["hello"], title="t", entry_renderer=renderer)
        assert mock_menu.call_args.kwargs["entry_renderer"] is renderer

    @patch(f"{_FZF}.terminal_menu", return_value=[])
    @patch(f"{_FZF}.sys")
    def test_returns_none_when_cancelled(self, mock_sys, mock_menu):
        mock_sys.stdin.isatty.return_value = True
        mock_sys.stdout.isatty.return_value = True
        assert _run_command_menu(["hello"], title="t") == (None, False)

    @patch(f"{_FZF}.terminal_menu")
    @patch(f"{_FZF}.sys")
    def test_requires_a_tty(self, mock_sys, mock_menu):
        mock_sys.stdin.isatty.return_value = False
        mock_sys.stdout.isatty.return_value = True
        from usecli.cli.core.exceptions import UsecliError

        with pytest.raises(UsecliError):
            _run_command_menu(["hello"], title="t")
        mock_menu.assert_not_called()

    @patch(f"{_FZF}.terminal_menu")
    def test_returns_none_without_entries(self, mock_menu):
        assert _run_command_menu([], title="t") == (None, False)
        mock_menu.assert_not_called()


class TestOpenTtyFd:
    @patch(f"{_FZF}.os.open", return_value=7)
    def test_opens_dev_tty_first(self, mock_open):
        assert _open_tty_fd() == 7
        mock_open.assert_called_once_with("/dev/tty", os.O_RDWR)

    @patch(f"{_FZF}.os.ttyname", return_value="/dev/ttys009")
    @patch(f"{_FZF}.os.open", side_effect=[OSError("no tty"), 8])
    def test_falls_back_to_the_stream_tty(self, mock_open, mock_ttyname):
        stdin = MagicMock()
        stdin.isatty.return_value = True
        stdin.fileno.return_value = 0
        stdout = MagicMock()
        stdout.isatty.return_value = False
        with patch(f"{_FZF}.sys") as mock_sys:
            mock_sys.stdin = stdin
            mock_sys.stdout = stdout
            assert _open_tty_fd() == 8
        mock_ttyname.assert_called_once_with(0)
        mock_open.assert_any_call("/dev/ttys009", os.O_RDWR)

    @patch(f"{_FZF}.os.open", side_effect=OSError("no tty"))
    def test_returns_none_when_no_tty(self, mock_open):
        with patch(f"{_FZF}.sys") as mock_sys:
            mock_sys.stdin = None
            mock_sys.stdout = None
            assert _open_tty_fd() is None

    @patch(f"{_FZF}.os.open", side_effect=OSError("no tty"))
    def test_skips_streams_that_cannot_report_a_tty(self, mock_open):
        broken = MagicMock()
        broken.isatty.side_effect = ValueError("closed")
        with patch(f"{_FZF}.sys") as mock_sys:
            mock_sys.stdin = broken
            mock_sys.stdout = None
            assert _open_tty_fd() is None


# ---------------------------------------------------------------------------
# _type_into_terminal
# ---------------------------------------------------------------------------


class TestTypeIntoTerminal:
    @patch(f"{_FZF}.fcntl.ioctl")
    @patch(f"{_FZF}.os.close")
    @patch(f"{_FZF}.os.open", return_value=9)
    def test_types_each_byte_into_the_tty(self, mock_open, mock_close, mock_ioctl):
        assert _type_into_terminal("ab") is True
        mock_open.assert_called_once_with("/dev/tty", os.O_RDWR)
        assert mock_ioctl.call_count == 2
        mock_ioctl.assert_any_call(9, termios.TIOCSTI, b"a")
        mock_ioctl.assert_any_call(9, termios.TIOCSTI, b"b")
        mock_close.assert_called_once_with(9)

    @patch(f"{_FZF}.fcntl.ioctl")
    @patch(f"{_FZF}.termios.tcsetattr")
    @patch(
        f"{_FZF}.termios.tcgetattr",
        return_value=[0, 0, 0, termios.ECHO, 0, 0, []],
    )
    @patch(f"{_FZF}.os.close")
    @patch(f"{_FZF}.os.open", return_value=9)
    def test_mutes_echo_while_typing_and_restores_it(
        self, mock_open, mock_close, mock_getattr, mock_setattr, mock_ioctl
    ):
        assert _type_into_terminal("x") is True
        muted, restored = mock_setattr.call_args_list
        assert muted.args[1] == termios.TCSANOW
        assert muted.args[2][3] & termios.ECHO == 0
        assert restored.args[2][3] & termios.ECHO == termios.ECHO
        mock_close.assert_called_once_with(9)

    @patch(f"{_FZF}.termios.tcsetattr")
    @patch(
        f"{_FZF}.termios.tcgetattr",
        return_value=[0, 0, 0, termios.ECHO, 0, 0, []],
    )
    @patch(f"{_FZF}.fcntl.ioctl", side_effect=OSError("blocked"))
    @patch(f"{_FZF}.os.close")
    @patch(f"{_FZF}.os.open", return_value=9)
    def test_returns_false_and_restores_echo_when_ioctl_is_blocked(
        self, mock_open, mock_close, mock_ioctl, mock_getattr, mock_setattr
    ):
        assert _type_into_terminal("x") is False
        assert mock_setattr.call_count == 2
        assert mock_setattr.call_args_list[1].args[2][3] & termios.ECHO
        mock_close.assert_called_once_with(9)

    @patch(
        f"{_FZF}.termios.tcsetattr",
        side_effect=[None, OSError("restore failed")],
    )
    @patch(
        f"{_FZF}.termios.tcgetattr",
        return_value=[0, 0, 0, termios.ECHO, 0, 0, []],
    )
    @patch(f"{_FZF}.fcntl.ioctl")
    @patch(f"{_FZF}.os.close")
    @patch(f"{_FZF}.os.open", return_value=9)
    def test_ignores_echo_restore_failure(
        self, mock_open, mock_close, mock_ioctl, mock_getattr, mock_setattr
    ):
        assert _type_into_terminal("x") is True
        mock_close.assert_called_once_with(9)

    @patch(f"{_FZF}.os.open", side_effect=OSError("no tty"))
    def test_returns_false_without_a_controlling_tty(self, mock_open):
        assert _type_into_terminal("x") is False

    @patch(f"{_FZF}.termios", new=SimpleNamespace())
    def test_returns_false_without_tiocsti(self):
        assert _type_into_terminal("x") is False


# ---------------------------------------------------------------------------
# _select_command and entry formatting
# ---------------------------------------------------------------------------


class TestSelectCommand:
    def test_builds_aligned_entries_with_fallbacks(self):
        commands = [
            {"name": "hello", "help": "Say hello"},
            {"name": "db:migrate", "help": ""},
        ]
        with patch(
            f"{_FZF}._run_command_menu",
            side_effect=lambda entries, **_: (entries[0], False),
        ) as menu:
            result = _select_command(commands, title="usecli » select a command")
        assert result == ("hello", False)
        entries = menu.call_args.args[0]
        assert entries[0].startswith("hello")
        assert "Say hello" in entries[0]
        assert "\x1f" not in entries[0]
        assert "Db migrate" in entries[1]

    def test_maps_selected_entry_back_to_its_name(self):
        commands = [
            {"name": "alpha", "help": "A"},
            {"name": "beta", "help": "B"},
        ]
        with patch(
            f"{_FZF}._run_command_menu",
            side_effect=lambda entries, **_: (entries[1], False),
        ):
            assert _select_command(commands, title="t") == ("beta", False)

    def test_propagates_print_only(self):
        commands = [
            {"name": "alpha", "help": "A"},
            {"name": "beta", "help": "B"},
        ]
        with patch(
            f"{_FZF}._run_command_menu",
            side_effect=lambda entries, **_: (entries[1], True),
        ):
            assert _select_command(commands, title="t") == ("beta", True)

    def test_returns_none_when_cancelled(self):
        commands = [{"name": "alpha", "help": "A"}]
        with patch(f"{_FZF}._run_command_menu", return_value=(None, False)):
            assert _select_command(commands, title="t") == (None, False)

    def test_returns_none_for_unknown_selection(self):
        commands = [{"name": "alpha", "help": "A"}]
        with patch(f"{_FZF}._run_command_menu", return_value=("not an entry", False)):
            assert _select_command(commands, title="t") == (None, False)

    def test_returns_none_without_commands(self):
        assert _select_command([], title="t") == (None, False)

    @patch(f"{_FZF}.shutil.get_terminal_size")
    def test_colors_entries_when_space_allows(self, mock_size):
        mock_size.return_value = os.terminal_size((200, 40))
        commands = [{"name": "hello", "help": "Say hello"}]
        captured = {}

        def fake_menu(entries, *, title, entry_renderer=None):
            captured["entry"] = entries[0]
            captured["renderer"] = entry_renderer
            return entries[0], False

        with patch(f"{_FZF}._run_command_menu", side_effect=fake_menu):
            assert _select_command(commands, title="t") == ("hello", False)

        from usecli.cli.config.colors import COLOR

        colored = captured["renderer"](captured["entry"])
        assert COLOR.ANSI.PRIMARY in colored
        assert COLOR.ANSI.FOREGROUND_MUTED in colored
        assert "Say hello" in colored

    @patch(f"{_FZF}.shutil.get_terminal_size")
    def test_colors_entry_without_description(self, mock_size):
        mock_size.return_value = os.terminal_size((200, 40))
        captured = {}

        def fake_menu(entries, *, title, entry_renderer=None):
            captured["entry"] = entries[0]
            captured["renderer"] = entry_renderer
            return entries[0], False

        with patch(f"{_FZF}._run_command_menu", side_effect=fake_menu):
            _select_command([{"name": "", "help": ""}], title="t")

        from usecli.cli.config.colors import COLOR

        assert captured["renderer"](captured["entry"]) == (
            f"{COLOR.ANSI.PRIMARY}{COLOR.ANSI.RESET}"
        )

    @patch(f"{_FZF}.shutil.get_terminal_size")
    def test_skips_entry_colors_when_terminal_is_narrow(self, mock_size):
        mock_size.return_value = os.terminal_size((60, 24))
        commands = [{"name": "hello", "help": "Say hello"}]
        captured = {}

        def fake_menu(entries, *, title, entry_renderer=None):
            captured["renderer"] = entry_renderer
            return entries[0], False

        with patch(f"{_FZF}._run_command_menu", side_effect=fake_menu):
            _select_command(commands, title="t")

        assert captured["renderer"] is None

    def test_humanize_name(self):
        assert _humanize_name("db:migrate-all") == "Db migrate all"

    def test_fit_truncates(self):
        assert _fit("abcdef", 4) == "abc…"
        assert _fit("abc", 4) == "abc"

    def test_fit_handles_tiny_widths(self):
        assert _fit("abc", 0) == ""
        assert _fit("abc", 1) == "…"

    def test_menu_entry_escapes_pipe(self):
        entry = _menu_entry("cmd", "a | b", 4)
        assert "a \\| b" in entry

    def test_menu_entry_without_description_is_just_the_name(self):
        assert _menu_entry("cmd", "", 8) == "cmd"


# ---------------------------------------------------------------------------
# run_interactive
# ---------------------------------------------------------------------------


class TestRunInteractive:
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value=(None, False),
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
        return_value=("test", False),
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

    @patch(f"{_FZF}._type_into_terminal", return_value=True)
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value=("test", True),
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command.subprocess.run"
    )
    @patch("usecli.cli.commands.defaults.base.internal.interactive_command.console")
    def test_tab_types_command_into_shell_line(
        self, mock_console, mock_run, mock_select, mock_type
    ):
        app = MagicMock()
        cmd = _cmd("test", "Test")
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app, extra_args=["--verbose"])
        mock_run.assert_not_called()
        mock_console.print.assert_not_called()
        typed = mock_type.call_args.args[0]
        assert typed.endswith(" test --verbose ")
        assert not typed.endswith("\n")

    @patch(
        "usecli.cli.utils.interactive.prompt_input.edit_line",
        return_value="custom-cmd --more",
    )
    @patch(f"{_FZF}._type_into_terminal", return_value=False)
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value=("test", True),
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command.subprocess.run"
    )
    @patch("usecli.cli.commands.defaults.base.internal.interactive_command.console")
    def test_tab_falls_back_to_editable_line_when_tty_rejects(
        self, mock_console, mock_run, mock_select, mock_type, mock_edit
    ):
        app = MagicMock()
        cmd = _cmd("test", "Test")
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app, extra_args=["--verbose"])
        mock_console.print.assert_not_called()
        mock_edit.assert_called_once()
        assert mock_edit.call_args.args[0].endswith(" test --verbose ")
        mock_run.assert_called_once_with("custom-cmd --more", shell=True, check=False)

    @patch(
        "usecli.cli.utils.interactive.prompt_input.edit_line",
        side_effect=KeyboardInterrupt,
    )
    @patch(f"{_FZF}._type_into_terminal", return_value=False)
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value=("test", True),
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command.subprocess.run"
    )
    def test_tab_editable_line_cancel_does_not_run(
        self, mock_run, mock_select, mock_type, mock_edit
    ):
        app = MagicMock()
        cmd = _cmd("test", "Test")
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app)
        mock_run.assert_not_called()

    @patch("usecli.cli.utils.interactive.prompt_input.edit_line", return_value="   ")
    @patch(f"{_FZF}._type_into_terminal", return_value=False)
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value=("test", True),
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command.subprocess.run"
    )
    def test_tab_editable_line_empty_does_not_run(
        self, mock_run, mock_select, mock_type, mock_edit
    ):
        app = MagicMock()
        cmd = _cmd("test", "Test")
        app.registered_commands = [cmd]
        with patch(
            "usecli.cli.commands.defaults.base.internal.interactive_command.typer.main.get_command"
        ) as mock_get_cmd:
            mock_get_cmd.return_value = MagicMock(spec=click.Group, commands={})
            run_interactive(app)
        mock_run.assert_not_called()

    @patch(f"{_FZF}._type_into_terminal", return_value=True)
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        side_effect=[("group", True), ("sub", False)],
    )
    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command.subprocess.run"
    )
    @patch("usecli.cli.commands.defaults.base.internal.interactive_command.console")
    def test_tab_on_group_keeps_prefill_for_subcommand(
        self, mock_console, mock_run, mock_select, mock_type
    ):
        app = MagicMock()
        app._usecli_group_aliases = {}
        group_cmd_entry = _cmd("group", "Group", is_group=True)
        sub_cmd = _cmd("sub", "Sub")
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
                run_interactive(app)
        mock_run.assert_not_called()
        mock_console.print.assert_not_called()
        assert mock_type.call_args.args[0].endswith(" group sub ")

    def test_raises_when_no_commands(self):
        app = MagicMock()
        app.registered_commands = []
        with pytest.raises(typer.Exit):
            run_interactive(app)

    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value=("test", False),
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
        return_value=("make:command", False),
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
        return_value=("test", False),
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
            mock_select.side_effect = [("test", False), ("test", False)]
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
        return_value=("group", False),
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
        return_value=("group", False),
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
                mock_select.side_effect = [("group", False), (None, False)]
                run_interactive(app)

    @patch(
        "usecli.cli.commands.defaults.base.internal.interactive_command._select_command",
        return_value=("group", False),
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
        return_value=("group", False),
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
        return_value=("test", False),
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
        return_value=("test", False),
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
        return_value=("test", False),
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
            patch(f"{_FZF}._select_command", return_value=("db:migrate", False)),
            patch(f"{_FZF}.subprocess.run", _mock_run()),
            _patch_get_command({}),
        ):
            run_interactive(app)


class TestRunInteractiveUnparseableSelection:
    def test_empty_cmd_name_raises(self):
        app = _make_app([_cmd("test", "Test")])
        with (
            patch(f"{_FZF}._select_command", return_value=("", False)),
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
            patch(f"{_FZF}._select_command", return_value=("sub", False)),
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
            patch(f"{_FZF}._select_command", return_value=("", False)),
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
                    patch(f"{_FZF}.console.input", side_effect=input_side_effect)
                )
            stack.enter_context(
                patch(
                    "builtins.input",
                    side_effect=AssertionError("builtin input used"),
                )
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
                patch(f"{_FZF}.console.input", side_effect=KeyboardInterrupt),
                patch(
                    "builtins.input",
                    side_effect=AssertionError("builtin input used"),
                ),
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
                    patch(f"{_FZF}.console.input", side_effect=input_side_effect)
                )
            stack.enter_context(
                patch(
                    "builtins.input",
                    side_effect=AssertionError("builtin input used"),
                )
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
                patch(f"{_FZF}.console.input", side_effect=KeyboardInterrupt),
                patch(
                    "builtins.input",
                    side_effect=AssertionError("builtin input used"),
                ),
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
            patch(f"{_FZF}.console.input", return_value="myvalue"),
            patch(
                "builtins.input",
                side_effect=AssertionError("builtin input used"),
            ),
            _patch_get_command({}),
        ):
            run_interactive(app, cmd_parts=["test"], extra_args=["--base"])
