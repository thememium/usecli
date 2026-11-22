"""Tests for framework-wide hidden options."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from usecli.cli.core.base_command import CustomHelpCommand
from usecli.cli.core.options import HiddenOptionsGroup, filter_universal_hidden_params


def _option(opts: list[str]) -> MagicMock:
    param = MagicMock()
    param.opts = opts
    return param


def _build_app() -> typer.Typer:
    app = typer.Typer(cls=HiddenOptionsGroup)

    @app.callback()
    def root(
        interactive: bool = typer.Option(False, "--interactive", "-i"),
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        _ = (interactive, json_output)

    @app.command(cls=CustomHelpCommand)
    def hello() -> None:
        pass

    return app


class TestFilterUniversalHiddenParams:
    def test_removes_only_universal_options(self):
        json_param = _option(["--json"])
        interactive = _option(["--interactive", "-i"])
        version = _option(["--version", "-v"])
        help_param = _option(["--help", "-h"])
        command = MagicMock()
        command.params = [json_param, interactive, version, help_param]

        with patch(
            "usecli.cli.core.options.hidden_option_names",
            return_value={"json", "interactive", "version", "help"},
        ):
            filter_universal_hidden_params(command)

        assert command.params == [version, help_param]

    def test_noop_without_hidden_options(self):
        json_param = _option(["--json"])
        command = MagicMock()
        command.params = [json_param]

        with patch("usecli.cli.core.options.hidden_option_names", return_value=set()):
            filter_universal_hidden_params(command)

        assert command.params == [json_param]


class TestHiddenOptionsIntegration:
    def test_command_help_hides_universal_options(self):
        with patch(
            "usecli.cli.core.options.hidden_option_names",
            return_value={"json", "interactive"},
        ):
            result = CliRunner().invoke(_build_app(), ["hello", "--help"])

        assert "--help" in result.output
        assert "--json" not in result.output
        assert "--interactive" not in result.output

    def test_group_help_hides_universal_options(self):
        with patch(
            "usecli.cli.core.options.hidden_option_names",
            return_value={"json", "interactive"},
        ):
            result = CliRunner().invoke(_build_app(), ["--help"])

        assert result.exit_code == 0, result.output
        assert "--help" in result.output
        assert "--json" not in result.output
        assert "--interactive" not in result.output
