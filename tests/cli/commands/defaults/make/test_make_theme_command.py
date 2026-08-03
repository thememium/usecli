"""Tests for usecli.cli.commands.defaults.make.make_theme_command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from usecli.cli.commands.defaults.make.make_theme_command import MakeThemeCommand
from usecli.shared.config.manager import reset_config


@pytest.fixture
def mock_typer_app():
    app = MagicMock()
    app.registered_commands = []
    app.command = MagicMock(return_value=lambda f: f)
    return app


@pytest.fixture
def make_theme_command(mock_typer_app):
    return MakeThemeCommand(app=mock_typer_app)


@pytest.fixture(autouse=True)
def reset_usecli_config():
    reset_config()
    yield
    reset_config()


class TestMakeThemeCommandSignature:
    def test_signature(self, make_theme_command):
        assert make_theme_command.signature() == "make:theme"

    def test_description(self, make_theme_command):
        assert isinstance(make_theme_command.description(), str)


class TestMakeThemeCommandVisibility:
    @patch("usecli.cli.commands.defaults.make.make_theme_command.sys")
    @patch("usecli.cli.commands.defaults.make.make_theme_command.os")
    def test_visible_when_usecli_command(self, mock_os, mock_sys, make_theme_command):
        mock_sys.argv = ["/usr/bin/usecli"]
        mock_os.path.basename.return_value = "usecli"
        assert make_theme_command.visible() is True

    @patch("usecli.cli.commands.defaults.make.make_theme_command.sys")
    @patch("usecli.cli.commands.defaults.make.make_theme_command.os")
    def test_not_visible_when_other_command(
        self, mock_os, mock_sys, make_theme_command
    ):
        mock_sys.argv = ["/usr/bin/mycli"]
        mock_os.path.basename.return_value = "mycli"
        assert make_theme_command.visible() is False


class TestMakeThemeCommandHandle:
    def test_rejects_empty_name(self, make_theme_command, capsys):
        make_theme_command.handle("   ")
        # Should print error and return without creating file

    def test_rejects_name_that_becomes_empty_after_strip_toml(
        self, tmp_path, monkeypatch, make_theme_command
    ):
        monkeypatch.chdir(tmp_path)
        make_theme_command.handle(".toml")
        # Should print error and return

    def test_creates_theme_file(self, tmp_path, monkeypatch, make_theme_command):
        monkeypatch.chdir(tmp_path)
        make_theme_command.handle("mytheme")

        themes_dir = tmp_path / "cli" / "themes"
        created = themes_dir / "mytheme.toml"
        assert created.exists()
        assert len(created.read_text()) > 0

    def test_strips_toml_extension(self, tmp_path, monkeypatch, make_theme_command):
        monkeypatch.chdir(tmp_path)
        make_theme_command.handle("mytheme.toml")

        themes_dir = tmp_path / "cli" / "themes"
        created = themes_dir / "mytheme.toml"
        assert created.exists()

    def test_handles_duplicate_names(self, tmp_path, monkeypatch, make_theme_command):
        monkeypatch.chdir(tmp_path)
        themes_dir = tmp_path / "cli" / "themes"
        themes_dir.mkdir(parents=True)
        (themes_dir / "mytheme.toml").write_text("existing")

        make_theme_command.handle("mytheme")

        created = themes_dir / "mytheme_1.toml"
        assert created.exists()

    def test_handles_multiple_duplicates(
        self, tmp_path, monkeypatch, make_theme_command
    ):
        monkeypatch.chdir(tmp_path)
        themes_dir = tmp_path / "cli" / "themes"
        themes_dir.mkdir(parents=True)
        (themes_dir / "mytheme.toml").write_text("existing")
        (themes_dir / "mytheme_1.toml").write_text("existing")

        make_theme_command.handle("mytheme")

        created = themes_dir / "mytheme_2.toml"
        assert created.exists()

    def test_uses_project_template_when_available(
        self, tmp_path, monkeypatch, make_theme_command
    ):
        monkeypatch.chdir(tmp_path)
        templates_dir = tmp_path / "cli" / "templates"
        templates_dir.mkdir(parents=True)
        (templates_dir / "theme.toml.j2").write_text("# Project theme template")

        make_theme_command.handle("custom")

        themes_dir = tmp_path / "cli" / "themes"
        created = themes_dir / "custom.toml"
        assert created.exists()
        assert created.read_text() == "# Project theme template"

    def test_falls_back_to_builtin_template(
        self, tmp_path, monkeypatch, make_theme_command
    ):
        monkeypatch.chdir(tmp_path)

        make_theme_command.handle("default")

        themes_dir = tmp_path / "cli" / "themes"
        created = themes_dir / "default.toml"
        assert created.exists()
        assert len(created.read_text()) > 0

    def test_creates_themes_dir_if_missing(
        self, tmp_path, monkeypatch, make_theme_command
    ):
        monkeypatch.chdir(tmp_path)
        # themes_dir doesn't exist yet

        make_theme_command.handle("newtheme")

        themes_dir = tmp_path / "cli" / "themes"
        assert themes_dir.exists()
        assert (themes_dir / "newtheme.toml").exists()

    @patch("usecli.cli.commands.defaults.make.make_theme_command.find_project_root")
    @patch("usecli.cli.commands.defaults.make.make_theme_command.reset_config")
    @patch("usecli.cli.commands.defaults.make.make_theme_command.get_config")
    def test_resets_config_when_root_mismatch(
        self,
        mock_get_config,
        mock_reset,
        mock_find_root,
        make_theme_command,
        tmp_path,
        monkeypatch,
    ):
        monkeypatch.chdir(tmp_path)

        mock_config = MagicMock()
        mock_config.get_project_root.return_value = Path("/different/root")
        mock_config.get_project_paths.return_value = {
            "themes_dir": tmp_path / "themes",
            "templates_dir": tmp_path / "templates",
        }
        mock_get_config.return_value = mock_config
        mock_find_root.return_value = tmp_path

        make_theme_command.handle("test")

        mock_reset.assert_called_once()
