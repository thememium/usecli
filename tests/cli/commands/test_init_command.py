"""Tests for InitCommand."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from usecli.cli.commands.init_command import InitCommand

DEFAULT_TITLE = "My CLI"
DEFAULT_DESCRIPTION = "A custom CLI tool"
DEFAULT_COMMANDS_DIR = "commands"


@pytest.fixture
def temp_project_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def mock_console():
    with patch("usecli.cli.commands.init_command.console"):
        yield


@pytest.fixture
def init_command(mock_console):
    mock_app = MagicMock()
    return InitCommand(mock_app)


class TestInitCommandDirectoryCreation:
    def test_creates_commands_directory(self, temp_project_dir, init_command):
        commands_dir = temp_project_dir / "commands"
        assert not commands_dir.exists()

        init_command.handle(
            DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=True
        )

        assert commands_dir.exists()
        assert commands_dir.is_dir()

    def test_creates_custom_commands_directory(self, temp_project_dir, init_command):
        custom_dir = "my_custom_commands"
        commands_path = temp_project_dir / custom_dir

        init_command.handle(DEFAULT_TITLE, DEFAULT_DESCRIPTION, custom_dir, force=True)

        assert commands_path.exists()
        assert commands_path.is_dir()

    def test_handles_existing_commands_directory(self, temp_project_dir, init_command):
        commands_dir = temp_project_dir / "commands"
        commands_dir.mkdir()

        init_command.handle(
            DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=True
        )

        assert commands_dir.exists()


class TestInitCommandPyprojectToml:
    def test_adds_config_to_existing_pyproject(self, temp_project_dir, init_command):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'test'\n")

        init_command.handle(
            "Test CLI", "Test description", DEFAULT_COMMANDS_DIR, force=True
        )

        content = pyproject.read_text()
        assert "[tool.usecli]" in content
        assert 'title = "Test CLI"' in content
        assert 'description = "Test description"' in content

    def test_skips_when_user_declines_overwrite(self, temp_project_dir, init_command):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[tool.usecli]\ntitle = "Existing"\n')

        with patch("rich.prompt.Confirm.ask") as mock_ask:
            mock_ask.return_value = False
            init_command.handle(
                DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, False
            )

        content = pyproject.read_text()
        assert 'title = "Existing"' in content
        assert 'title = "My CLI"' not in content

    def test_overwrites_when_user_accepts(self, temp_project_dir, init_command):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[tool.usecli]\ntitle = "Existing"\n')

        with patch("rich.prompt.Confirm.ask") as mock_ask:
            mock_ask.return_value = True
            init_command.handle(
                "New CLI", "New description", DEFAULT_COMMANDS_DIR, False
            )

        content = pyproject.read_text()
        assert 'title = "New CLI"' in content
        assert "New description" in content

    def test_overwrites_with_force_flag(self, temp_project_dir, init_command):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[tool.usecli]\ntitle = "Existing"\n')

        init_command.handle(
            "Forced CLI", "Forced description", DEFAULT_COMMANDS_DIR, force=True
        )

        content = pyproject.read_text()
        assert 'title = "Forced CLI"' in content
        assert "Forced description" in content

    def test_preserves_existing_pyproject_content(self, temp_project_dir, init_command):
        pyproject = temp_project_dir / "pyproject.toml"
        original_content = "[project]\nname = 'my-project'\nversion = '1.0.0'\n"
        pyproject.write_text(original_content)

        init_command.handle(
            DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=True
        )

        content = pyproject.read_text()
        assert "[project]" in content
        assert "name = 'my-project'" in content
        assert "version = '1.0.0'" in content
        assert "[tool.usecli]" in content


class TestInitCommandStandaloneConfig:
    def test_creates_usecli_config_toml_when_no_pyproject(
        self, temp_project_dir, init_command
    ):
        config_path = temp_project_dir / "usecli.config.toml"
        assert not config_path.exists()

        init_command.handle("My CLI", "A test CLI", DEFAULT_COMMANDS_DIR, force=True)

        assert config_path.exists()
        content = config_path.read_text()
        assert "[tool.usecli]" in content
        assert 'title = "My CLI"' in content
        assert 'description = "A test CLI"' in content

    def test_standalone_config_has_correct_format(self, temp_project_dir, init_command):
        config_path = temp_project_dir / "usecli.config.toml"

        init_command.handle("Test CLI", "Test description", "custom_cmds", force=True)

        content = config_path.read_text()
        assert "[tool.usecli]" in content
        assert 'title = "Test CLI"' in content
        assert 'description = "Test description"' in content
        assert 'commands_dir = "custom_cmds"' in content
        assert "show_setup = true" in content

    def test_prompts_to_overwrite_existing_standalone_config(
        self, temp_project_dir, init_command
    ):
        config_path = temp_project_dir / "usecli.config.toml"
        config_path.write_text('[tool.usecli]\ntitle = "Old"\n')

        with patch("rich.prompt.Confirm.ask") as mock_ask:
            mock_ask.return_value = False
            init_command.handle(
                DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, False
            )

        content = config_path.read_text()
        assert 'title = "Old"' in content


class TestInitCommandOptions:
    def test_custom_title(self, temp_project_dir, init_command):
        config_path = temp_project_dir / "usecli.config.toml"

        init_command.handle(
            "Custom CLI Title", DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=True
        )

        content = config_path.read_text()
        assert 'title = "Custom CLI Title"' in content

    def test_custom_description(self, temp_project_dir, init_command):
        config_path = temp_project_dir / "usecli.config.toml"

        init_command.handle(
            DEFAULT_TITLE, "My custom description", DEFAULT_COMMANDS_DIR, force=True
        )

        content = config_path.read_text()
        assert 'description = "My custom description"' in content

    def test_custom_commands_dir(self, temp_project_dir, init_command):
        custom_dir = temp_project_dir / "my_commands"
        config_path = temp_project_dir / "usecli.config.toml"

        init_command.handle(
            DEFAULT_TITLE, DEFAULT_DESCRIPTION, "my_commands", force=True
        )

        assert custom_dir.exists()
        content = config_path.read_text()
        assert 'commands_dir = "my_commands"' in content


class TestInitCommandDefaults:
    def test_default_values(self, temp_project_dir, init_command):
        config_path = temp_project_dir / "usecli.config.toml"

        init_command.handle(
            DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=True
        )

        content = config_path.read_text()
        assert 'title = "My CLI"' in content
        assert 'description = "A custom CLI tool"' in content
        assert 'commands_dir = "commands"' in content
        assert "show_setup = true" in content


class TestInitCommandIntegration:
    def test_full_init_workflow_with_pyproject(self, temp_project_dir, init_command):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'test-project'\n")
        commands_dir = temp_project_dir / "commands"

        init_command.handle(
            "Integration Test CLI",
            "Integration test description",
            "commands",
            force=True,
        )

        assert commands_dir.exists()

        pyproject_content = pyproject.read_text()
        assert "[tool.usecli]" in pyproject_content
        assert 'title = "Integration Test CLI"' in pyproject_content

        config_toml = temp_project_dir / "usecli.config.toml"
        assert not config_toml.exists()

    def test_full_init_workflow_without_pyproject(self, temp_project_dir, init_command):
        commands_dir = temp_project_dir / "commands"
        config_toml = temp_project_dir / "usecli.config.toml"

        init_command.handle(
            "Standalone Test CLI",
            "Standalone test description",
            DEFAULT_COMMANDS_DIR,
            force=True,
        )

        assert commands_dir.exists()
        assert config_toml.exists()
        content = config_toml.read_text()
        assert 'title = "Standalone Test CLI"' in content

        pyproject = temp_project_dir / "pyproject.toml"
        assert not pyproject.exists()
