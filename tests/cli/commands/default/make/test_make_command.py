from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from usecli.cli.commands.defaults.make.make_command import MakeCommand
from usecli.shared.config.manager import reset_config


@pytest.fixture
def mock_typer_app():
    app = MagicMock()
    app.registered_commands = []
    app.command = MagicMock(return_value=lambda f: f)
    return app


@pytest.fixture
def make_command(mock_typer_app):
    return MakeCommand(app=mock_typer_app)


@pytest.fixture(autouse=True)
def reset_usecli_config():
    reset_config()
    yield
    reset_config()


class TestMakeCommandSignature:
    def test_signature_returns_make_command(self, make_command):
        assert make_command.signature() == "make:command"

    def test_description_returns_string(self, make_command):
        description = make_command.description()
        assert isinstance(description, str)
        assert len(description) > 0


class TestMakeCommandTemplates:
    def test_prefers_project_template(self, tmp_path, monkeypatch, make_command):
        templates_dir = tmp_path / "cli" / "templates"
        templates_dir.mkdir(parents=True)
        template_path = templates_dir / "command.py.j2"
        template_path.write_text("Project: {{ command_name }}")
        monkeypatch.chdir(tmp_path)

        make_command.handle("hello")

        created = tmp_path / "cli" / "commands" / "hello_command.py"
        assert created.exists()
        assert created.read_text() == "Project: hello"

    def test_falls_back_to_builtin_template(self, tmp_path, monkeypatch, make_command):
        monkeypatch.chdir(tmp_path)

        make_command.handle("world")

        created = tmp_path / "cli" / "commands" / "world_command.py"
        assert created.exists()
        assert "class WorldCommand" in created.read_text()
