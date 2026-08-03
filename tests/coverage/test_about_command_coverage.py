"""Coverage-focused tests for usecli.cli.commands.defaults.base.about_command.

Targets uncovered lines without modifying source:

- lines 40-45: ``_toml_decode_error`` (recursive helper)
- lines 123-124: ``_get_dependencies`` swallows an OSError while reading pyproject
- line 133: ``_get_dependencies`` skips non-string dependency entries
- lines 144-147: ``_get_application_distribution`` falls back to the primary
  command name when the argv-derived distribution is not found
- lines 189-190: ``_get_project_description`` swallows an OSError
- lines 237-238: ``_get_script_commands`` swallows an OSError
- lines 242-244: ``_get_script_commands`` handles a non-dict ``scripts`` value

Note: line 34 (``import tomli as tomllib``) is only reachable on Python < 3.11
and is therefore not covered on the 3.12 test interpreter.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from usecli.cli.commands.defaults.base.about_command import (
    _get_application_distribution,
    _get_dependencies,
    _get_project_description,
    _get_script_commands,
    _load_toml,
    _toml_decode_error,
)


class TestTomlDecodeError:
    def test_recurses(self):
        """The helper always calls itself, so invoking it raises RecursionError."""
        with pytest.raises(RecursionError):
            _toml_decode_error()


class TestLoadTomlPy310:
    def test_loads_with_tomli_on_py310(self):
        """On Python < 3.11, _load_toml imports tomli (line 34)."""
        from usecli.cli.commands.defaults.base import about_command

        with patch.object(about_command.sys, "version_info", (3, 10)):
            result = _load_toml("key = 1")
        assert result == {"key": 1}


class TestTomlDecodeErrorPy310:
    def test_recurses_on_py310(self):
        """On Python < 3.11, the else branch (line 43) is covered."""
        from usecli.cli.commands.defaults.base import about_command

        with (
            patch.object(about_command.sys, "version_info", (3, 10)),
            pytest.raises(RecursionError),
        ):
            _toml_decode_error()


class TestGetDependenciesOSError:
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_console_script_distribution",
        return_value=None,
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name", return_value=None)
    @patch(
        "usecli.cli.commands.defaults.base.about_command._load_toml",
        side_effect=OSError("boom"),
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._toml_decode_error",
        return_value=OSError,
    )
    def test_os_error_reading_pyproject_returns_empty(
        self, mock_tde, mock_load, mock_name, mock_find, tmp_path
    ):
        config = MagicMock()
        config.pyproject_path = tmp_path / "pyproject.toml"
        config.pyproject_path.write_text("x")
        assert _get_dependencies(config) == []


class TestGetDependenciesSkipsNonString:
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_console_script_distribution",
        return_value=None,
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name", return_value=None)
    def test_skips_non_string_dependency(self, mock_name, mock_find, tmp_path):
        config = MagicMock()
        config.pyproject_path = tmp_path / "pyproject.toml"
        config.pyproject_path.write_text(
            '[project]\ndependencies = ["requests>=2.0", 42]'
        )
        result = _get_dependencies(config)
        assert result == [("requests", ">=2.0")]


class TestGetApplicationDistributionFallback:
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_console_script_distribution",
        return_value=None,
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name", return_value="mycli")
    def test_falls_back_to_primary_command(self, mock_name, mock_find):
        result = _get_application_distribution()
        assert result is None
        # Called once for argv-derived name and once for the primary command
        assert mock_find.call_count == 2


class TestGetProjectDescriptionOSError:
    @patch(
        "usecli.cli.commands.defaults.base.about_command._load_toml",
        side_effect=OSError("boom"),
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._toml_decode_error",
        return_value=OSError,
    )
    def test_os_error_returns_none(self, mock_tde, mock_load, tmp_path):
        config = MagicMock()
        config.pyproject_path = tmp_path / "pyproject.toml"
        config.pyproject_path.write_text("x")
        assert _get_project_description(config) is None


class TestGetScriptCommandsOSError:
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_installed_script_commands",
        return_value=[],
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name", return_value=None)
    @patch(
        "usecli.cli.commands.defaults.base.about_command._load_toml",
        side_effect=OSError("boom"),
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._toml_decode_error",
        return_value=OSError,
    )
    def test_os_error_returns_empty(
        self, mock_tde, mock_load, mock_name, mock_installed, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text("x")
        assert _get_script_commands() == []


class TestGetScriptCommandsNonDictScripts:
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_installed_script_commands",
        return_value=[],
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name", return_value="mycli")
    def test_non_dict_scripts_with_primary_returns_primary(
        self, mock_name, mock_installed, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nscripts = "not a dict"')
        assert _get_script_commands() == ["mycli"]

    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_installed_script_commands",
        return_value=[],
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name", return_value=None)
    def test_non_dict_scripts_without_primary_returns_empty(
        self, mock_name, mock_installed, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "pyproject.toml").write_text('[project]\nscripts = "not a dict"')
        assert _get_script_commands() == []
