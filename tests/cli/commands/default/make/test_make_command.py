from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

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

    def test_handles_colon_in_name(self, tmp_path, monkeypatch, make_command):
        monkeypatch.chdir(tmp_path)

        make_command.handle("my:command")

        # When name contains colon, it uses the raw clean_name as command_name
        # and snakecase for the file name
        created = tmp_path / "cli" / "commands" / "my_command.py"
        assert created.exists()

    def test_handles_space_in_name(self, tmp_path, monkeypatch, make_command):
        monkeypatch.chdir(tmp_path)

        make_command.handle("my command")

        created = tmp_path / "cli" / "commands" / "my_command.py"
        assert created.exists()

    def test_rejects_existing_file(self, tmp_path, monkeypatch, make_command):
        monkeypatch.chdir(tmp_path)
        commands_dir = tmp_path / "cli" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "existing_command.py").write_text("existing")

        make_command.handle("existing")
        # Should print error and return without overwriting
        assert (commands_dir / "existing_command.py").read_text() == "existing"

    @patch("usecli.cli.commands.defaults.make.make_command.find_project_root")
    @patch("usecli.cli.commands.defaults.make.make_command.reset_config")
    @patch("usecli.cli.commands.defaults.make.make_command.get_config")
    def test_resets_config_when_root_mismatch(
        self,
        mock_get_config,
        mock_reset,
        mock_find_root,
        tmp_path,
        monkeypatch,
        make_command,
    ):
        monkeypatch.chdir(tmp_path)

        mock_config = MagicMock()
        mock_config.get_project_root.return_value = Path("/different/root")
        mock_config.get_project_paths.return_value = {
            "commands_dir": tmp_path / "commands",
            "templates_dir": tmp_path / "templates",
        }
        mock_get_config.return_value = mock_config
        mock_find_root.return_value = tmp_path

        make_command.handle("test")

        mock_reset.assert_called_once()
