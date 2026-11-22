"""Tests for usecli.cli.commands.defaults.make.make_skill_command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from usecli.cli.commands.defaults.make.make_skill_command import MakeSkillCommand
from usecli.cli.core.exceptions import UsecliBadParameter
from usecli.scaffold import _frontmatter_description
from usecli.shared.config.manager import reset_config


@pytest.fixture
def mock_typer_app():
    app = MagicMock()
    app.registered_commands = []
    app.command = MagicMock(return_value=lambda f: f)
    return app


@pytest.fixture
def make_skill_command(mock_typer_app):
    return MakeSkillCommand(app=mock_typer_app)


@pytest.fixture(autouse=True)
def reset_usecli_config():
    reset_config()
    yield
    reset_config()


class TestMakeSkillCommandMetadata:
    def test_signature(self, make_skill_command):
        assert make_skill_command.signature() == "make:skill"

    def test_description(self, make_skill_command):
        assert make_skill_command.description() == "Create a new bundled skill"


class TestFrontmatterDescription:
    def test_normalizes_whitespace_and_escapes_quotes(self):
        assert _frontmatter_description(' line one\n line "two" ') == (
            'line one line \\"two\\"'
        )

    def test_escapes_backslashes(self):
        assert _frontmatter_description("a\\b") == "a\\\\b"


class TestMakeSkillHandle:
    def _config(self, tmp_path: Path, command_name: str = "mycli"):
        config = MagicMock()
        config.get_project_root.return_value = tmp_path
        config.get_project_skills_dir.return_value = tmp_path / "skills"
        config.get_project_templates_dir.return_value = tmp_path / "templates"
        config.get.return_value = command_name
        return config

    @patch("usecli.cli.commands.defaults.make.make_skill_command.find_project_root")
    @patch("usecli.cli.commands.defaults.make.make_skill_command.get_config")
    def test_creates_skill_file(
        self,
        mock_get_config,
        mock_find_root,
        make_skill_command,
        tmp_path,
    ):
        mock_get_config.return_value = self._config(tmp_path)
        mock_find_root.return_value = tmp_path

        make_skill_command.handle("deploy-checks", description="Check deployments")

        target = tmp_path / "skills" / "deploy-checks" / "SKILL.md"
        content = target.read_text()
        assert "name: deploy-checks" in content
        assert 'description: "Check deployments"' in content
        assert "Re-run `mycli skill:install`" in content

    @patch("usecli.cli.commands.defaults.make.make_skill_command.find_project_root")
    @patch("usecli.cli.commands.defaults.make.make_skill_command.get_config")
    def test_uses_a_default_description(
        self,
        mock_get_config,
        mock_find_root,
        make_skill_command,
        tmp_path,
    ):
        mock_get_config.return_value = self._config(tmp_path)
        mock_find_root.return_value = tmp_path

        make_skill_command.handle("deploy-checks")

        content = (tmp_path / "skills" / "deploy-checks" / "SKILL.md").read_text()
        assert "Use the deploy-checks skill with the mycli CLI." in content

    @patch("usecli.cli.commands.defaults.make.make_skill_command.find_project_root")
    @patch("usecli.cli.commands.defaults.make.make_skill_command.get_config")
    def test_falls_back_to_usecli_command_name(
        self,
        mock_get_config,
        mock_find_root,
        make_skill_command,
        tmp_path,
    ):
        mock_get_config.return_value = self._config(tmp_path, command_name="")
        mock_find_root.return_value = tmp_path

        make_skill_command.handle("deploy-checks")

        content = (tmp_path / "skills" / "deploy-checks" / "SKILL.md").read_text()
        assert "usecli skill:install" in content

    @patch("usecli.cli.commands.defaults.make.make_skill_command.find_project_root")
    @patch("usecli.cli.commands.defaults.make.make_skill_command.get_config")
    def test_rejects_existing_skill(
        self,
        mock_get_config,
        mock_find_root,
        make_skill_command,
        tmp_path,
    ):
        mock_get_config.return_value = self._config(tmp_path)
        mock_find_root.return_value = tmp_path
        target = tmp_path / "skills" / "deploy-checks" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("existing")

        make_skill_command.handle("deploy-checks")

        assert target.read_text() == "existing"

    def test_rejects_invalid_name(self, make_skill_command):
        with pytest.raises(UsecliBadParameter, match="Invalid skill name"):
            make_skill_command.handle("Not Valid")

    @patch("usecli.cli.commands.defaults.make.make_skill_command.reset_config")
    @patch("usecli.cli.commands.defaults.make.make_skill_command.find_project_root")
    @patch("usecli.cli.commands.defaults.make.make_skill_command.get_config")
    def test_resets_config_when_root_differs(
        self,
        mock_get_config,
        mock_find_root,
        mock_reset,
        make_skill_command,
        tmp_path,
    ):
        first = self._config(tmp_path)
        first.get_project_root.return_value = Path("/different/root")
        second = self._config(tmp_path)
        mock_get_config.side_effect = [first, second]
        mock_find_root.return_value = tmp_path

        make_skill_command.handle("deploy-checks")

        mock_reset.assert_called_once()
        assert (tmp_path / "skills" / "deploy-checks" / "SKILL.md").exists()
