"""Regression tests for ClickException handling on the invoke path.

``UsecliError`` extends real-click ``ClickException`` while typer raises its
vendored ``typer._click`` exceptions. Both output modes must handle both
hierarchies: human mode shows the styled error and exits non-zero instead of
leaking a traceback, and JSON mode emits the error envelope.
"""

from __future__ import annotations

import pytest
import typer

import usecli
from usecli.cli.core.exceptions.base import UsecliError


@pytest.fixture
def error_app():
    _ = usecli.app  # ensure the framework (and PrefixMatchingGroup) is initialized
    app = typer.Typer(cls=usecli.PrefixMatchingGroup)

    @app.command()
    def noop() -> None:
        return None

    @app.command()
    def boom(
        json_output: bool = typer.Option(
            False, "--json", help="Emit one machine-readable JSON document."
        ),
    ) -> None:
        raise UsecliError("kaboom", suggestion="try again")

    return app


class TestHumanMode:
    def test_shows_styled_error_and_exits_nonzero(self, error_app, capsys):
        with pytest.raises(SystemExit) as excinfo:
            error_app(["boom"], standalone_mode=False)

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "kaboom" in captured.err
        assert "try again" in captured.err


class TestJsonMode:
    def test_emits_error_envelope_and_exits_nonzero(self, error_app, capsys):
        with pytest.raises(SystemExit) as excinfo:
            error_app(["boom", "--json"])

        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert '"ok":false' in captured.out
        assert '"UsecliError"' in captured.out
        assert '"kaboom"' in captured.out
