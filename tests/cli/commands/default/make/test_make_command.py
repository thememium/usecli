from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from usecli.cli.commands.defaults.make.make_command import MakeCommand


@pytest.fixture
def mock_typer_app():
    app = MagicMock()
    app.registered_commands = []
    app.command = MagicMock(return_value=lambda f: f)
    return app


@pytest.fixture
def make_command(mock_typer_app):
    return MakeCommand(app=mock_typer_app)


class TestMakeCommandSignature:
    def test_signature_returns_make_command(self, make_command):
        assert make_command.signature() == "make:command"

    def test_description_returns_string(self, make_command):
        description = make_command.description()
        assert isinstance(description, str)
        assert len(description) > 0
