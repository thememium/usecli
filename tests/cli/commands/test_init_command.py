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
    """Fixture providing a temporary project directory."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def mock_console():
    """Fixture providing a mock console."""
    with patch("usecli.cli.commands.init_command.console") as mock:
        yield mock


@pytest.fixture
def init_command(mock_console):
    """Fixture providing an InitCommand instance."""
    mock_app = MagicMock()
    cmd = InitCommand(mock_app)
    return cmd


class TestInitCommandDirectoryCreation:
    """Tests for commands directory creation."""

    def test_creates_commands_directory(self, temp_project_dir, init_command):
        """Test that init creates the commands directory."""
        commands_dir = temp_project_dir / "commands"
        assert not commands_dir.exists()

        init_command.handle(DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR)

        assert commands_dir.exists()
        assert commands_dir.is_dir()

    def test_creates_custom_commands_directory(self, temp_project_dir, init_command):
        """Test that init creates a custom commands directory."""
        custom_dir = "my_custom_commands"
        commands_path = temp_project_dir / custom_dir

        init_command.handle(DEFAULT_TITLE, DEFAULT_DESCRIPTION, custom_dir)

        assert commands_path.exists()
        assert commands_path.is_dir()

    def test_handles_existing_commands_directory(self, temp_project_dir, init_command):
        """Test that init handles an existing commands directory gracefully."""
        commands_dir = temp_project_dir / "commands"
        commands_dir.mkdir()

        init_command.handle(DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR)

        assert commands_dir.exists()


class TestInitCommandPyprojectToml:
    """Tests for pyproject.toml integration."""

    def test_adds_config_to_existing_pyproject(self, temp_project_dir, init_command):
        """Test that init adds [tool.usecli] to existing pyproject.toml."""
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'test'\n")

        init_command.handle("Test CLI", "Test description", DEFAULT_COMMANDS_DIR)

        content = pyproject.read_text()
        assert "[tool.usecli]" in content
        assert 'title = "Test CLI"' in content
        assert 'description = "Test description"' in content

    def test_warns_when_tool_usecli_exists(self, temp_project_dir, init_command):
        """Test that init warns when [tool.usecli] already exists."""
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[tool.usecli]\ntitle = "Existing"\n')

        init_command.handle(DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR)

        content = pyproject.read_text()
        assert 'title = "Existing"' in content
        assert 'title = "My CLI"' not in content

    def test_preserves_existing_pyproject_content(self, temp_project_dir, init_command):
        """Test that init preserves existing pyproject.toml content."""
        pyproject = temp_project_dir / "pyproject.toml"
        original_content = "[project]\nname = 'my-project'\nversion = '1.0.0'\n"
        pyproject.write_text(original_content)

        init_command.handle(DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR)

        content = pyproject.read_text()
        assert "[project]" in content
        assert "name = 'my-project'" in content
        assert "version = '1.0.0'" in content
        assert "[tool.usecli]" in content


class TestInitCommandStandaloneConfig:
    """Tests for standalone usecli.config.toml creation."""

    def test_creates_usecli_config_toml_when_no_pyproject(
        self, temp_project_dir, init_command
    ):
        """Test that init creates usecli.config.toml when pyproject.toml doesn't exist."""
        config_path = temp_project_dir / "usecli.config.toml"
        assert not config_path.exists()

        init_command.handle("My CLI", "A test CLI", DEFAULT_COMMANDS_DIR)

        assert config_path.exists()
        content = config_path.read_text()
        assert "[tool.usecli]" in content
        assert 'title = "My CLI"' in content
        assert 'description = "A test CLI"' in content

    def test_standalone_config_has_correct_format(self, temp_project_dir, init_command):
        """Test that standalone config has the correct format."""
        config_path = temp_project_dir / "usecli.config.toml"

        init_command.handle("Test CLI", "Test description", "custom_cmds")

        content = config_path.read_text()
        assert "[tool.usecli]" in content
        assert 'title = "Test CLI"' in content
        assert 'description = "Test description"' in content
        assert 'commands_dir = "custom_cmds"' in content
        assert "show_setup = true" in content


class TestInitCommandOptions:
    """Tests for init command options."""

    def test_custom_title(self, temp_project_dir, init_command):
        """Test that custom title is used in config."""
        config_path = temp_project_dir / "usecli.config.toml"

        init_command.handle(
            "Custom CLI Title", DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR
        )

        content = config_path.read_text()
        assert 'title = "Custom CLI Title"' in content

    def test_custom_description(self, temp_project_dir, init_command):
        """Test that custom description is used in config."""
        config_path = temp_project_dir / "usecli.config.toml"

        init_command.handle(
            DEFAULT_TITLE, "My custom description", DEFAULT_COMMANDS_DIR
        )

        content = config_path.read_text()
        assert 'description = "My custom description"' in content

    def test_custom_commands_dir(self, temp_project_dir, init_command):
        """Test that custom commands_dir is used in config and directory."""
        custom_dir = temp_project_dir / "my_commands"
        config_path = temp_project_dir / "usecli.config.toml"

        init_command.handle(DEFAULT_TITLE, DEFAULT_DESCRIPTION, "my_commands")

        assert custom_dir.exists()
        content = config_path.read_text()
        assert 'commands_dir = "my_commands"' in content


class TestInitCommandDefaults:
    """Tests for init command default values."""

    def test_default_values(self, temp_project_dir, init_command):
        """Test that default values are used when options not provided."""
        config_path = temp_project_dir / "usecli.config.toml"

        init_command.handle(DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR)

        content = config_path.read_text()
        assert 'title = "My CLI"' in content
        assert 'description = "A custom CLI tool"' in content
        assert 'commands_dir = "commands"' in content
        assert "show_setup = true" in content


class TestInitCommandIntegration:
    """Integration tests for init command."""

    def test_full_init_workflow_with_pyproject(self, temp_project_dir, init_command):
        """Test full init workflow when pyproject.toml exists."""
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'test-project'\n")
        commands_dir = temp_project_dir / "commands"

        init_command.handle(
            "Integration Test CLI",
            "Integration test description",
            "commands",
        )

        assert commands_dir.exists()

        pyproject_content = pyproject.read_text()
        assert "[tool.usecli]" in pyproject_content
        assert 'title = "Integration Test CLI"' in pyproject_content

        config_toml = temp_project_dir / "usecli.config.toml"
        assert not config_toml.exists()

    def test_full_init_workflow_without_pyproject(self, temp_project_dir, init_command):
        """Test full init workflow when pyproject.toml doesn't exist."""
        commands_dir = temp_project_dir / "commands"
        config_toml = temp_project_dir / "usecli.config.toml"

        init_command.handle(
            "Standalone Test CLI",
            "Standalone test description",
            DEFAULT_COMMANDS_DIR,
        )

        assert commands_dir.exists()
        assert config_toml.exists()
        content = config_toml.read_text()
        assert 'title = "Standalone Test CLI"' in content

        pyproject = temp_project_dir / "pyproject.toml"
        assert not pyproject.exists()
