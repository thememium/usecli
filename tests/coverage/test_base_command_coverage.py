"""Coverage-focused tests for usecli.cli.core.base_command.

Targets uncovered branches in ``NestedCommandRegistry`` (group callback help /
interactive / command listing, ``register_command``) and ``BaseCommand`` alias
normalization and registration paths, without modifying source.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from usecli.cli.core.base_command import BaseCommand, NestedCommandRegistry


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


# =============================================================================
# NestedCommandRegistry group callback
# =============================================================================


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


# =============================================================================
# NestedCommandRegistry.register_command
# =============================================================================


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


# =============================================================================
# BaseCommand._register_with_aliases (line 477: skip duplicate/self alias)
# =============================================================================


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


# =============================================================================
# BaseCommand._register_group_aliases (line 515: skip self/duplicate group alias)
# =============================================================================


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


# =============================================================================
# BaseCommand._normalize_aliases
# =============================================================================


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


# =============================================================================
# BaseCommand._normalize_nested_aliases
# =============================================================================


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
