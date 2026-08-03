"""Coverage-focused tests for InitCommand.

Targets uncovered branches in src/usecli/cli/commands/init_command.py that are
not exercised by tests/cli/commands/test_init_command.py. Only adds new tests;
does not modify any source or existing test files.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from usecli.cli.commands.init_command import InitCommand

DEFAULT_TITLE = "My CLI"
DEFAULT_DESCRIPTION = "A custom CLI tool"
DEFAULT_COMMANDS_DIR = "cli/commands"


@pytest.fixture
def temp_project_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def mock_console():
    with patch("usecli.cli.commands.init_command.console"):
        yield


@pytest.fixture
def init_cmd(mock_console):
    return InitCommand(app=MagicMock())


@pytest.fixture
def interactive_cmd(mock_console):
    """InitCommand with interactive prompts/menus mocked to their defaults."""
    with (
        patch("usecli.cli.commands.init_command.Prompt.ask") as mock_prompt,
        patch("usecli.cli.commands.init_command.terminal_menu") as mock_terminal_menu,
    ):
        mock_prompt.side_effect = lambda *args, **kwargs: kwargs.get("default", "")

        def _menu_side_effect(options, *args, **kwargs):
            if isinstance(options, list) and "big" in options:
                return ["big"]
            return ["default"]

        mock_terminal_menu.side_effect = _menu_side_effect
        yield InitCommand(MagicMock())


class TestInitCommandBasics:
    def test_signature(self, init_cmd):
        assert init_cmd.signature() == "init"

    def test_description(self, init_cmd):
        assert init_cmd.description() == "Initialize usecli in the current project"


class TestBuildSystemHelpers:
    def test_ensure_build_system_missing_file(self, init_cmd, tmp_path):
        assert init_cmd._ensure_build_system(tmp_path / "nope.toml") is False

    def test_ensure_build_system_already_present(self, init_cmd, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[build-system]\nrequires = []\n")
        assert init_cmd._ensure_build_system(pyproject) is False

    def test_package_discovery_missing_file(self, init_cmd, tmp_path):
        assert (
            init_cmd._add_setuptools_package_discovery(
                tmp_path / "nope.toml", "cli/commands"
            )
            is False
        )

    def test_package_discovery_already_present(self, init_cmd, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.setuptools.packages.find]\nwhere = ['.']\n")
        assert (
            init_cmd._add_setuptools_package_discovery(pyproject, "cli/commands")
            is False
        )

    def test_package_discovery_empty_commands_dir(self, init_cmd, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\n")
        assert init_cmd._add_setuptools_package_discovery(pyproject, "") is False

    def test_package_data_missing_file(self, init_cmd, tmp_path):
        assert (
            init_cmd._add_setuptools_package_data(
                tmp_path / "nope.toml", "cli/commands"
            )
            is False
        )

    def test_package_data_empty_commands_dir(self, init_cmd, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\n")
        assert init_cmd._add_setuptools_package_data(pyproject, "") is False


class TestShouldSkipConfigPath:
    def test_resolve_oserror_falls_back(self, init_cmd, tmp_path):
        target = tmp_path / "config.toml"
        real_resolve = Path.resolve

        def _fake_resolve(self, *args, **kwargs):
            if self == target:
                raise OSError("boom")
            return real_resolve(self, *args, **kwargs)

        with patch.object(Path, "resolve", _fake_resolve):
            # No skip dirs and not under sys.prefix -> False
            assert init_cmd._should_skip_config_path(target) is False

    def test_under_sys_prefix_returns_true(self, init_cmd, tmp_path, monkeypatch):
        monkeypatch.setattr(sys, "prefix", str(tmp_path))
        target = tmp_path / "config.toml"
        assert init_cmd._should_skip_config_path(target) is True


class TestEnsureProjectScripts:
    def test_declines_overwrite_existing_entry(self, init_cmd, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project.scripts]\nmycli = "other:main"\n')
        with patch("usecli.cli.commands.init_command.Confirm.ask", return_value=False):
            result = init_cmd._ensure_project_scripts(pyproject, "mycli", force=False)
        assert result == "skipped"
        assert 'mycli = "other:main"' in pyproject.read_text()


class TestInferCommandsDir:
    def test_invalid_toml_falls_back(self, init_cmd, tmp_path):
        (tmp_path / "pyproject.toml").write_text("not = = valid")
        assert init_cmd._infer_commands_dir(tmp_path) == "cli/commands"


class TestGetExistingScriptName:
    def test_scripts_not_a_dict(self, init_cmd, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nscripts = "not-a-dict"\n')
        assert init_cmd._get_existing_usecli_script_name(pyproject) is None


class TestPromptCommandName:
    def test_retries_after_invalid(self, init_cmd):
        with (
            patch(
                "usecli.cli.commands.init_command.Prompt.ask",
                side_effect=["invalid name!", "validcli"],
            ),
            patch("usecli.cli.core.exceptions.UsecliBadParameter.show") as mock_show,
        ):
            result = init_cmd._prompt_command_name("default")
        assert result == "validcli"
        mock_show.assert_called_once()


class TestLoadThemeColors:
    def test_colors_not_a_dict(self, init_cmd, tmp_path):
        theme = tmp_path / "theme.toml"
        theme.write_text('colors = "not-a-dict"\n')
        assert init_cmd._load_theme_colors(theme) == {}


class TestGetThemeFiles:
    def test_skips_non_file_matches(self, init_cmd, tmp_path):
        themes_path = tmp_path / "themes"
        themes_path.mkdir()
        (themes_path / "not_a_file.toml").mkdir()
        with patch(
            "usecli.cli.commands.init_command.THEMES_DIR", tmp_path / "missing_themes"
        ):
            assert init_cmd._get_theme_files(themes_path) == []


class TestPromptTheme:
    def test_no_theme_files_returns_default(self, init_cmd, tmp_path):
        themes_path = tmp_path / "themes"
        themes_path.mkdir()
        with patch(
            "usecli.cli.commands.init_command.THEMES_DIR", tmp_path / "missing_themes"
        ):
            assert init_cmd._prompt_theme(themes_path) == "default"


class TestHandleJsonMode:
    def _setup(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"\n')
        (tmp_path / ".venv").mkdir()

    def test_json_mode_success(self, temp_project_dir, init_cmd):
        self._setup(temp_project_dir)
        with (
            patch(
                "usecli.cli.commands.init_command.shutil.which",
                return_value="/usr/bin/uv",
            ),
            patch(
                "usecli.cli.commands.init_command.subprocess.run",
                return_value=MagicMock(returncode=0),
            ),
        ):
            result = init_cmd._handle_json_mode(
                title="My CLI",
                description="A custom CLI tool for testing",
                commands_dir=None,
                templates_dir=None,
                themes_dir=None,
                config_path=None,
                command_name="mycli",
                force=True,
                theme="default",
                title_font="big",
            )
        assert result["command_name"] == "mycli"
        assert result["config_status"] == "created"
        assert (temp_project_dir / "cli" / "usecli.config.toml").exists()

    def test_handle_dispatches_to_json_mode(self, temp_project_dir, init_cmd):
        self._setup(temp_project_dir)
        with (
            patch("usecli.cli.core.runtime.is_json_mode", return_value=True),
            patch(
                "usecli.cli.commands.init_command.shutil.which",
                return_value="/usr/bin/uv",
            ),
            patch(
                "usecli.cli.commands.init_command.subprocess.run",
                return_value=MagicMock(returncode=0),
            ),
        ):
            result = init_cmd.handle(
                title="My CLI",
                description="A custom CLI tool for testing",
                commands_dir=None,
                templates_dir=None,
                themes_dir=None,
                config_path=None,
                command_name="mycli",
                force=True,
                theme="default",
                title_font="big",
            )
        assert result["command_name"] == "mycli"

    def test_json_mode_no_pyproject(self, temp_project_dir, init_cmd):
        with (
            patch(
                "usecli.cli.commands.init_command.shutil.which",
                return_value="/usr/bin/uv",
            ),
            patch(
                "usecli.cli.commands.init_command.subprocess.run",
                return_value=MagicMock(returncode=0),
            ),
        ):
            result = init_cmd._handle_json_mode(
                title="My CLI",
                description="A custom CLI tool for testing",
                commands_dir=None,
                templates_dir=None,
                themes_dir=None,
                config_path=None,
                command_name="mycli",
                force=True,
                theme="default",
                title_font="big",
            )
        assert result["scripts_status"] == "added"
        assert (temp_project_dir / "pyproject.toml").exists()

    def test_json_mode_with_config_path(self, temp_project_dir, init_cmd):
        self._setup(temp_project_dir)
        with (
            patch(
                "usecli.cli.commands.init_command.shutil.which",
                return_value="/usr/bin/uv",
            ),
            patch(
                "usecli.cli.commands.init_command.subprocess.run",
                return_value=MagicMock(returncode=0),
            ),
        ):
            result = init_cmd._handle_json_mode(
                title="My CLI",
                description="A custom CLI tool for testing",
                commands_dir=None,
                templates_dir=None,
                themes_dir=None,
                config_path="custom/config.toml",
                command_name="mycli",
                force=True,
                theme="default",
                title_font="big",
            )
        assert (temp_project_dir / "custom" / "config.toml").exists()
        assert result["config_status"] == "created"

    def test_json_mode_skips_resolved_config_path(self, temp_project_dir, init_cmd):
        self._setup(temp_project_dir)
        with (
            patch.object(init_cmd, "_should_skip_config_path", return_value=True),
            patch(
                "usecli.cli.commands.init_command.shutil.which",
                return_value="/usr/bin/uv",
            ),
            patch(
                "usecli.cli.commands.init_command.subprocess.run",
                return_value=MagicMock(returncode=0),
            ),
        ):
            result = init_cmd._handle_json_mode(
                title="My CLI",
                description="A custom CLI tool for testing",
                commands_dir=None,
                templates_dir=None,
                themes_dir=None,
                config_path=None,
                command_name="mycli",
                force=True,
                theme="default",
                title_font="big",
            )
        assert result["config_status"] == "created"


class TestHandleInteractiveBranches:
    def test_infers_commands_dir_and_uses_project_title(
        self, temp_project_dir, interactive_cmd
    ):
        (temp_project_dir / "pyproject.toml").write_text('[project]\nname = "test"\n')
        interactive_cmd.handle(
            title="Use CLI",
            description=DEFAULT_DESCRIPTION,
            commands_dir=None,
            force=True,
        )
        config = (temp_project_dir / "cli" / "usecli.config.toml").read_text()
        assert 'title = "test"' in config

    def test_make_template_already_exists(self, temp_project_dir, interactive_cmd):
        templates = temp_project_dir / "cli" / "templates"
        templates.mkdir(parents=True)
        (templates / "command.py.j2").write_text("existing")
        interactive_cmd.handle(
            DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=True
        )
        assert (templates / "command.py.j2").read_text() == "existing"

    def test_theme_template_already_exists(self, temp_project_dir, interactive_cmd):
        themes = temp_project_dir / "cli" / "themes"
        themes.mkdir(parents=True)
        (themes / "default.toml").write_text("existing")
        interactive_cmd.handle(
            DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=True
        )
        assert (themes / "default.toml").read_text() == "existing"

    def test_skipped_scripts_status(self, temp_project_dir, interactive_cmd):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "test"\n\n[project.scripts]\ntest = "other:main"\n'
        )
        with patch("usecli.cli.commands.init_command.Confirm.ask", return_value=False):
            interactive_cmd.handle(
                DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=False
            )
        assert 'test = "other:main"' in pyproject.read_text()

    def test_skips_skipped_default_config_path(self, temp_project_dir, interactive_cmd):
        (temp_project_dir / "pyproject.toml").write_text('[project]\nname = "test"\n')
        with patch.object(
            interactive_cmd, "_should_skip_config_path", return_value=True
        ):
            interactive_cmd.handle(
                DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=True
            )
        assert (temp_project_dir / "cli" / "usecli.config.toml").exists()

    def test_replace_existing_config_at_new_location(
        self, temp_project_dir, interactive_cmd
    ):
        (temp_project_dir / "pyproject.toml").write_text('[project]\nname = "test"\n')
        existing = temp_project_dir / "cli" / "usecli.config.toml"
        existing.parent.mkdir(parents=True)
        existing.write_text('[usecli]\ntitle = "Old"\n')
        custom = temp_project_dir / "custom" / "usecli.config.toml"

        with (
            patch("usecli.cli.commands.init_command.Prompt.ask") as mock_prompt,
            patch("usecli.cli.commands.init_command.Confirm.ask", return_value=True),
        ):

            def _prompt_side_effect(*args, **kwargs):
                if args and "Config file location" in args[0]:
                    return str(custom)
                return kwargs.get("default", "")

            mock_prompt.side_effect = _prompt_side_effect
            interactive_cmd.handle(
                DEFAULT_TITLE, DEFAULT_DESCRIPTION, DEFAULT_COMMANDS_DIR, force=False
            )

        # The existing config was replaced in place rather than writing to custom.
        content = existing.read_text()
        assert 'title = "My CLI"' in content
        assert not custom.exists()
