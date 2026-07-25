"""Tests for the interactive command builder/fzf utilities."""

from __future__ import annotations

import click
from typer.core import TyperOption

from usecli.cli.commands.defaults.base.internal.fzf_command import (
    _get_optional_options,
)


class TestGetOptionalOptions:
    """Tests for _get_optional_options filtering."""

    def test_returns_user_declared_option(self):
        cmd = click.Command("demo", params=[click.Option(["--env"])])
        options = _get_optional_options(cmd)
        assert any("--env" in names for _, names, _, _ in options)

    def test_excludes_help_option(self):
        cmd = click.Command("demo", params=[click.Option(["--help"])])
        assert _get_optional_options(cmd) == []

    def test_excludes_interactive_option(self):
        cmd = click.Command(
            "demo", params=[click.Option(["--interactive", "-i"], is_flag=True)]
        )
        assert _get_optional_options(cmd) == []

    def test_excludes_json_option(self):
        cmd = click.Command(
            "demo", params=[TyperOption(param_decls=["--json"], is_flag=True)]
        )
        assert _get_optional_options(cmd) == []

    def test_excludes_json_option_with_short_alias(self):
        cmd = click.Command(
            "demo",
            params=[TyperOption(param_decls=["-j", "--json"], is_flag=True)],
        )
        assert _get_optional_options(cmd) == []
