"""Tests for InitCommand."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
import usecli

local_usecli_path = Path(__file__).resolve().parents[3] / "src" / "usecli"
if str(local_usecli_path) not in list(usecli.__path__):
    usecli.__path__ = list(usecli.__path__) + [str(local_usecli_path)]
importlib.invalidate_caches()

from usecli.cli.commands.init_command import InitCommand  # noqa: E402

DEFAULT_TITLE = "My CLI"
DEFAULT_DESCRIPTION = "A custom CLI tool"
DEFAULT_COMMANDS_DIR = "cli/commands"
DEFAULT_TEMPLATES_DIR = "cli/templates"


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
    with patch("usecli.cli.commands.init_command.Prompt.ask") as mock_prompt:
        with patch(
            "usecli.cli.commands.init_command.terminal_menu"
        ) as mock_terminal_menu:
            mock_prompt.side_effect = lambda *args, **kwargs: kwargs.get("default", "")
            mock_terminal_menu.return_value = ["big"]
            mock_app = MagicMock()
            yield InitCommand(mock_app)


class TestInitCommandDirectoryCreation:
    def test_creates_commands_directory(self, temp_project_dir, init_command):
        commands_dir = temp_project_dir / "cli" / "commands"
        templates_dir = temp_project_dir / "cli" / "templates"
        cli_dir = temp_project_dir / "cli"
        assert not commands_dir.exists()

        init_command.handle(
            DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=True
        )

        assert commands_dir.exists()
        assert commands_dir.is_dir()
        assert templates_dir.exists()
        assert templates_dir.is_dir()
        assert (cli_dir / "__init__.py").exists()
        assert (commands_dir / "__init__.py").exists()
        assert (templates_dir / "command.py.j2").exists()

    def test_creates_custom_commands_directory(self, temp_project_dir, init_command):
        custom_dir = "my_custom_commands"
        commands_path = temp_project_dir / custom_dir
        templates_path = temp_project_dir / "templates"

        init_command.handle(DEFAULT_TITLE, DEFAULT_DESCRIPTION, custom_dir, force=True)

        assert commands_path.exists()
        assert commands_path.is_dir()
        assert templates_path.exists()
        assert templates_path.is_dir()
        assert (commands_path / "__init__.py").exists()
        assert (templates_path / "command.py.j2").exists()

    def test_handles_existing_commands_directory(self, temp_project_dir, init_command):
        commands_dir = temp_project_dir / "cli" / "commands"
        commands_dir.mkdir(parents=True)
        templates_dir = temp_project_dir / "cli" / "templates"
        templates_dir.mkdir(parents=True)

        init_command.handle(
            DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=True
        )

        assert commands_dir.exists()
        assert (commands_dir / "__init__.py").exists()
        assert templates_dir.exists()


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

    def test_auto_syncs_when_venv_exists(self, temp_project_dir, init_command):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text(
            "[project]\nname = 'test'\n\n[project.scripts]\nmycli = \"usecli:run_app\"\n"
        )
        (temp_project_dir / ".venv").mkdir()

        with patch("usecli.cli.commands.init_command.shutil.which") as mock_which:
            with patch("usecli.cli.commands.init_command.subprocess.run") as mock_run:
                mock_which.return_value = "/usr/bin/uv"
                mock_run.return_value = MagicMock(returncode=0)

                init_command.handle(
                    DEFAULT_TITLE,
                    DEFAULT_DESCRIPTION,
                    DEFAULT_COMMANDS_DIR,
                    force=True,
                )

                mock_run.assert_called_once_with(
                    ["/usr/bin/uv", "sync"],
                    capture_output=True,
                    text=True,
                )

    def test_skips_auto_sync_without_venv(self, temp_project_dir, init_command):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text(
            "[project]\nname = 'test'\n\n[project.scripts]\nmycli = \"usecli:run_app\"\n"
        )

        with patch("usecli.cli.commands.init_command.subprocess.run") as mock_run:
            init_command.handle(
                DEFAULT_TITLE,
                DEFAULT_DESCRIPTION,
                DEFAULT_COMMANDS_DIR,
                force=True,
            )

            mock_run.assert_not_called()

    def test_adds_build_system_when_missing(self, temp_project_dir, init_command):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text(
            "[project]\nname = 'test'\n\n[project.scripts]\nmycli = \"usecli:run_app\"\n"
        )

        init_command.handle(
            DEFAULT_TITLE,
            DEFAULT_DESCRIPTION,
            DEFAULT_COMMANDS_DIR,
            force=True,
        )

        content = pyproject.read_text()
        assert "[build-system]" in content
        assert 'build-backend = "setuptools.build_meta"' in content
        assert content.strip().endswith('build-backend = "setuptools.build_meta"')

    def test_adds_setuptools_package_discovery(self, temp_project_dir, init_command):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text(
            "[project]\nname = 'test'\n\n[project.scripts]\nmycli = \"usecli:run_app\"\n"
        )

        init_command.handle(
            DEFAULT_TITLE,
            DEFAULT_DESCRIPTION,
            DEFAULT_COMMANDS_DIR,
            force=True,
        )

        content = pyproject.read_text()
        assert "[tool.setuptools.packages.find]" in content
        assert 'where = ["."]' in content
        assert 'include = ["cli*"]' in content

    def test_adds_project_script_entry(self, temp_project_dir, init_command):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'test'\n")

        init_command.handle(
            DEFAULT_TITLE,
            DEFAULT_DESCRIPTION,
            DEFAULT_COMMANDS_DIR,
            force=True,
        )

        content = pyproject.read_text()
        assert "[project.scripts]" in content
        assert 'usecli = "usecli:run_app"' in content

    def test_preserves_existing_project_script_entries(
        self, temp_project_dir, init_command
    ):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text(
            "[project]\nname = 'test'\n\n[project.scripts]\nfoo = \"foo:main\"\n"
        )

        init_command.handle(
            DEFAULT_TITLE,
            DEFAULT_DESCRIPTION,
            DEFAULT_COMMANDS_DIR,
            force=True,
        )

        content = pyproject.read_text()
        assert "[project.scripts]" in content
        assert 'foo = "foo:main"' in content
        assert 'usecli = "usecli:run_app"' in content

    def test_prompts_before_overwriting_project_script_entry(
        self, temp_project_dir, init_command
    ):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text(
            "[project]\nname = 'test'\n\n[project.scripts]\nusecli = \"other:main\"\n"
        )

        with patch("rich.prompt.Confirm.ask") as mock_ask:
            mock_ask.return_value = False
            init_command.handle(
                DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=False
            )

        content = pyproject.read_text()
        assert 'usecli = "other:main"' in content
        assert 'usecli = "usecli:run_app"' not in content

    def test_overwrites_project_script_entry_with_force(
        self, temp_project_dir, init_command
    ):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text(
            "[project]\nname = 'test'\n\n[project.scripts]\nusecli = \"other:main\"\n"
        )

        init_command.handle(
            DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=True
        )

        content = pyproject.read_text()
        assert 'usecli = "usecli:run_app"' in content

    def test_skips_when_user_declines_overwrite(self, temp_project_dir, init_command):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[tool.usecli]\ntitle = "Existing"\n')

        with patch("rich.prompt.Confirm.ask") as mock_ask:
            mock_ask.return_value = False
            init_command.handle(
                DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=False
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
                "New CLI", "New description", DEFAULT_COMMANDS_DIR, force=False
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
        assert 'templates_dir = "templates"' in content

    def test_prompts_to_overwrite_existing_standalone_config(
        self, temp_project_dir, init_command
    ):
        config_path = temp_project_dir / "usecli.config.toml"
        config_path.write_text('[tool.usecli]\ntitle = "Old"\n')

        with patch("rich.prompt.Confirm.ask") as mock_ask:
            mock_ask.return_value = False
            init_command.handle(
                DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=False
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
        assert 'templates_dir = "templates"' in content


class TestInitCommandDefaults:
    def test_default_values(self, temp_project_dir, init_command):
        config_path = temp_project_dir / "usecli.config.toml"

        init_command.handle(
            DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=True
        )

        content = config_path.read_text()
        assert 'title = "My CLI"' in content
        assert 'description = "A custom CLI tool"' in content
        assert 'commands_dir = "cli/commands"' in content
        assert 'templates_dir = "cli/templates"' in content
        assert 'title_font = "big"' in content
        assert "hide_init = false" in content
        assert "hide_inspire = false" in content
        assert "hide_make_command = false" in content


class TestInitCommandIntegration:
    def test_full_init_workflow_with_pyproject(self, temp_project_dir, init_command):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'test-project'\n")
        commands_dir = temp_project_dir / "cli" / "commands"

        init_command.handle(
            "Integration Test CLI",
            "Integration test description",
            DEFAULT_COMMANDS_DIR,
            force=True,
        )

        assert commands_dir.exists()

        pyproject_content = pyproject.read_text()
        assert "[tool.usecli]" in pyproject_content
        assert 'title = "Integration Test CLI"' in pyproject_content

        config_toml = temp_project_dir / "usecli.config.toml"
        assert not config_toml.exists()

    def test_full_init_workflow_without_pyproject(self, temp_project_dir, init_command):
        commands_dir = temp_project_dir / "cli" / "commands"
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
