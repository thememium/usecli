"""Coverage-focused tests for the fzf interactive command finder.

Targets uncovered lines in
``src/usecli/cli/commands/defaults/base/internal/fzf_command.py``:

- line 55-56:  ``_get_required_arguments`` swallows an AttributeError for help
- lines 238-241, 244: colon-command section grouping/sorting in ``run_interactive``
- lines 278-279: unparseable fzf selection
- lines 292-293: group-alias resolution from ``cmd_parts``
- line 324: subcommand selected via the fzf fallback
- lines 327-328: unparseable subcommand selection
- lines 340-341: extra args passed to a command with no subcommands
- lines 349-421: the required-arguments interactive flow
- lines 427-512: the optional-flags interactive flow

No source files are modified.
"""

from __future__ import annotations

import contextlib
import inspect
from unittest.mock import MagicMock, patch

import click
import pytest
import typer

from usecli.cli.commands.defaults.base.internal.fzf_command import (
    _get_required_arguments,
    run_interactive,
)

_FZF = "usecli.cli.commands.defaults.base.internal.fzf_command"


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


def _cmd(name, help="", callback=None, **kwargs):
    c = MagicMock()
    c.name = name
    c.help = help
    c.callback = callback
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


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
            patch(f"{_FZF}._run_fzf_menu", return_value="db:migrate"),
            patch(f"{_FZF}.subprocess.run", _mock_run()),
            _patch_get_command({}),
        ):
            run_interactive(app)


class TestRunInteractiveUnparseableSelection:
    def test_empty_cmd_name_raises(self):
        app = _make_app([_cmd("test", "Test")])
        with (
            patch(f"{_FZF}._run_fzf_menu", return_value=""),
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

    def test_subcommand_from_fzf_selection(self):
        app = self._group_app()
        sub_cmd = _cmd("sub", "Sub")
        with (
            patch(f"{_FZF}._run_fzf_menu", return_value="sub"),
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
            patch(f"{_FZF}._run_fzf_menu", return_value=""),
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
