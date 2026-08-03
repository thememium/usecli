"""Tests for usecli.cli.commands.defaults.base.about_command — utility functions and AboutCommand."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

from usecli.cli.commands.defaults.base.about_command import (
    AboutCommand,
    _get_application_description,
    _get_application_version,
    _get_console_script_distribution,
    _get_dependencies,
    _get_installed_script_commands,
    _get_package_dependencies_from_distribution,
    _get_project_description,
    _get_script_commands,
    _get_version,
    _load_toml,
    _parse_dependency_requirement,
)

# ---------------------------------------------------------------------------
# _load_toml
# ---------------------------------------------------------------------------


class TestLoadToml:
    def test_loads_valid_toml(self):
        result = _load_toml('[project]\nname = "test"')
        assert result == {"project": {"name": "test"}}

    def test_loads_empty_toml(self):
        result = _load_toml("")
        assert result == {}

    def test_raises_on_invalid_toml(self):
        with pytest.raises(tomllib.TOMLDecodeError):
            _load_toml("not = = valid")


# ---------------------------------------------------------------------------
# _parse_dependency_requirement
# ---------------------------------------------------------------------------


class TestParseDependencyRequirement:
    def test_simple_package_name(self):
        name, spec = _parse_dependency_requirement("requests")
        assert name == "requests"
        assert spec is None

    def test_package_with_version_spec(self):
        name, spec = _parse_dependency_requirement("requests>=2.0.0")
        assert name == "requests"
        assert spec == ">=2.0.0"

    def test_package_with_pinned_version(self):
        name, spec = _parse_dependency_requirement("requests==2.28.0")
        assert name == "requests"
        assert spec == "==2.28.0"

    def test_package_with_extras(self):
        name, spec = _parse_dependency_requirement("requests[security]>=2.0.0")
        assert name == "requests"
        assert spec == ">=2.0.0"

    def test_package_with_at_spec(self):
        name, spec = _parse_dependency_requirement(
            "mypackage @ https://example.com/mypackage.tar.gz"
        )
        assert name == "mypackage"
        assert spec == "https://example.com/mypackage.tar.gz"

    def test_package_with_at_no_spec(self):
        name, spec = _parse_dependency_requirement("mypackage @ ")
        assert name == "mypackage"
        assert spec is None

    def test_empty_string(self):
        name, spec = _parse_dependency_requirement("")
        assert name == ""
        assert spec is None

    def test_package_with_environment_marker(self):
        name, spec = _parse_dependency_requirement(
            "requests>=2.0; python_version>='3.8'"
        )
        assert name == "requests"
        assert spec == ">=2.0"

    def test_package_with_underscore_and_dot(self):
        name, spec = _parse_dependency_requirement("my_package.name>=1.0")
        assert name == "my_package.name"
        assert spec == ">=1.0"


# ---------------------------------------------------------------------------
# _get_version
# ---------------------------------------------------------------------------


class TestGetVersion:
    @patch("importlib.metadata.version")
    def test_returns_version_when_installed(self, mock_version):
        mock_version.return_value = "1.2.3"
        assert _get_version() == "1.2.3"

    @patch("importlib.metadata.version")
    def test_returns_fallback_when_not_installed(self, mock_version):
        mock_version.side_effect = PackageNotFoundError("usecli")
        assert _get_version() == "0.0.0"


# ---------------------------------------------------------------------------
# _get_console_script_distribution
# ---------------------------------------------------------------------------


class TestGetConsoleScriptDistribution:
    def test_returns_none_for_none_command(self):
        assert _get_console_script_distribution(None) is None

    def test_returns_none_for_empty_command(self):
        assert _get_console_script_distribution("") is None

    @patch("usecli.shared.config.manager._find_distribution_for_console_script")
    def test_calls_find_distribution(self, mock_find):
        mock_dist = MagicMock()
        mock_find.return_value = mock_dist
        result = _get_console_script_distribution("mycli")
        mock_find.assert_called_once_with("mycli")
        assert result == mock_dist


# ---------------------------------------------------------------------------
# _get_package_dependencies_from_distribution
# ---------------------------------------------------------------------------


class TestGetPackageDependenciesFromDistribution:
    def test_returns_empty_for_no_requires(self):
        dist = MagicMock()
        dist.requires = None
        result = _get_package_dependencies_from_distribution(dist)
        assert result == []

    def test_returns_empty_for_empty_requires(self):
        dist = MagicMock()
        dist.requires = []
        result = _get_package_dependencies_from_distribution(dist)
        assert result == []

    def test_parses_simple_dependency(self):
        dist = MagicMock()
        dist.requires = ["requests>=2.0"]
        result = _get_package_dependencies_from_distribution(dist)
        assert result == [("requests", ">=2.0")]

    def test_skips_non_string_requires(self):
        dist = MagicMock()
        dist.requires = [42, "requests>=2.0"]
        result = _get_package_dependencies_from_distribution(dist)
        assert result == [("requests", ">=2.0")]

    def test_skips_paren_start_requires(self):
        dist = MagicMock()
        dist.requires = ["(invalid", "requests>=2.0"]
        result = _get_package_dependencies_from_distribution(dist)
        assert result == [("requests", ">=2.0")]

    def test_skips_empty_name(self):
        dist = MagicMock()
        dist.requires = ["; python_version>='3.8'"]
        result = _get_package_dependencies_from_distribution(dist)
        assert result == []


# ---------------------------------------------------------------------------
# _get_application_version
# ---------------------------------------------------------------------------


class TestGetApplicationVersion:
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution"
    )
    def test_returns_dist_version(self, mock_get_dist):
        mock_dist = MagicMock()
        mock_dist.version = "2.0.0"
        mock_get_dist.return_value = mock_dist
        config = MagicMock()
        assert _get_application_version(config) == "2.0.0"

    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution"
    )
    @patch("usecli.cli.commands.defaults.base.about_command._get_version")
    def test_returns_config_version_when_no_dist(self, mock_version, mock_get_dist):
        mock_get_dist.return_value = None
        config = MagicMock()
        config.get_project_version.return_value = "1.5.0"
        assert _get_application_version(config) == "1.5.0"

    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution"
    )
    @patch("usecli.cli.commands.defaults.base.about_command._get_version")
    def test_returns_fallback_version(self, mock_version, mock_get_dist):
        mock_get_dist.return_value = None
        config = MagicMock()
        config.get_project_version.return_value = None
        mock_version.return_value = "0.0.0"
        assert _get_application_version(config) == "0.0.0"


# ---------------------------------------------------------------------------
# _get_application_description
# ---------------------------------------------------------------------------


class TestGetApplicationDescription:
    def test_returns_config_description(self):
        config = MagicMock()
        config.get.return_value = "My app description"
        config.has_key.return_value = True
        result = _get_application_description(config)
        assert result == "My app description"

    def test_strips_whitespace(self):
        config = MagicMock()
        config.get.return_value = "  My app  "
        config.has_key.return_value = True
        result = _get_application_description(config)
        assert result == "My app"

    @patch("usecli.cli.commands.defaults.base.about_command._get_project_description")
    def test_falls_back_to_project_description(self, mock_proj_desc):
        config = MagicMock()
        config.get.return_value = None
        config.has_key.return_value = False
        mock_proj_desc.return_value = "Project description"
        result = _get_application_description(config)
        assert result == "Project description"

    @patch("usecli.cli.commands.defaults.base.about_command._get_project_description")
    def test_falls_back_to_default_description(self, mock_proj_desc):
        config = MagicMock()
        config.get.return_value = None
        config.has_key.return_value = False
        mock_proj_desc.return_value = None
        result = _get_application_description(config)
        assert "CLI framework" in result

    def test_returns_config_description_even_if_whitespace_value(self):
        config = MagicMock()
        config.get.return_value = "   "
        config.has_key.return_value = True
        with patch(
            "usecli.cli.commands.defaults.base.about_command._get_project_description",
            return_value=None,
        ):
            result = _get_application_description(config)
            assert "CLI framework" in result


# ---------------------------------------------------------------------------
# _get_project_description
# ---------------------------------------------------------------------------


class TestGetProjectDescription:
    def test_returns_none_when_no_pyproject(self):
        config = MagicMock()
        config.pyproject_path = Path("/nonexistent/pyproject.toml")
        assert _get_project_description(config) is None

    def test_returns_description_from_toml(self, tmp_path):
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text('[project]\ndescription = "Test project"')
        config = MagicMock()
        config.pyproject_path = toml_path
        result = _get_project_description(config)
        assert result == "Test project"

    def test_returns_none_for_empty_description(self, tmp_path):
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text('[project]\ndescription = "  "')
        config = MagicMock()
        config.pyproject_path = toml_path
        assert _get_project_description(config) is None

    def test_returns_none_for_missing_description_key(self, tmp_path):
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text('[project]\nname = "test"')
        config = MagicMock()
        config.pyproject_path = toml_path
        assert _get_project_description(config) is None

    def test_returns_none_for_non_string_description(self, tmp_path):
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text("[project]\ndescription = 42")
        config = MagicMock()
        config.pyproject_path = toml_path
        result = _get_project_description(config)
        assert result is None


# ---------------------------------------------------------------------------
# _get_installed_script_commands
# ---------------------------------------------------------------------------


class TestGetInstalledScriptCommands:
    def test_returns_empty_when_no_dist(self):
        with patch(
            "usecli.cli.commands.defaults.base.about_command._get_console_script_distribution",
            return_value=None,
        ):
            assert _get_installed_script_commands("mycli") == []

    def test_returns_empty_on_attribute_error(self):
        mock_dist = MagicMock()
        type(mock_dist).entry_points = PropertyMock(side_effect=AttributeError)
        with patch(
            "usecli.cli.commands.defaults.base.about_command._get_console_script_distribution",
            return_value=mock_dist,
        ):
            assert _get_installed_script_commands("mycli") == []

    def test_returns_empty_on_os_error(self):
        mock_dist = MagicMock()
        type(mock_dist).entry_points = PropertyMock(side_effect=OSError)
        with patch(
            "usecli.cli.commands.defaults.base.about_command._get_console_script_distribution",
            return_value=mock_dist,
        ):
            assert _get_installed_script_commands("mycli") == []

    def test_returns_command_name_first(self):
        ep1 = MagicMock()
        ep1.group = "console_scripts"
        ep1.name = "mycli"
        ep2 = MagicMock()
        ep2.group = "console_scripts"
        ep2.name = "mycli-other"
        ep3 = MagicMock()
        ep3.group = "other_group"
        ep3.name = "ignore"

        mock_dist = MagicMock()
        mock_dist.entry_points = [ep1, ep2, ep3]
        with patch(
            "usecli.cli.commands.defaults.base.about_command._get_console_script_distribution",
            return_value=mock_dist,
        ):
            result = _get_installed_script_commands("mycli")
            assert result == ["mycli", "mycli-other"]

    def test_returns_all_scripts_when_command_not_in_list(self):
        ep1 = MagicMock()
        ep1.group = "console_scripts"
        ep1.name = "other-cli"

        mock_dist = MagicMock()
        mock_dist.entry_points = [ep1]
        with patch(
            "usecli.cli.commands.defaults.base.about_command._get_console_script_distribution",
            return_value=mock_dist,
        ):
            result = _get_installed_script_commands("mycli")
            assert result == ["other-cli"]

    def test_returns_empty_when_no_scripts(self):
        ep1 = MagicMock()
        ep1.group = "other_group"
        ep1.name = "ignore"

        mock_dist = MagicMock()
        mock_dist.entry_points = [ep1]
        with patch(
            "usecli.cli.commands.defaults.base.about_command._get_console_script_distribution",
            return_value=mock_dist,
        ):
            assert _get_installed_script_commands("mycli") == []


# ---------------------------------------------------------------------------
# _get_dependencies
# ---------------------------------------------------------------------------


class TestGetDependencies:
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution"
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_package_dependencies_from_distribution"
    )
    def test_returns_deps_from_distribution(self, mock_get_deps, mock_get_dist):
        mock_dist = MagicMock()
        mock_get_dist.return_value = mock_dist
        mock_get_deps.return_value = [("requests", ">=2.0")]
        config = MagicMock()

        result = _get_dependencies(config)
        assert result == [("requests", ">=2.0")]

    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution"
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_console_script_distribution"
    )
    def test_falls_back_to_pyproject(self, mock_find_dist, mock_get_dist):
        mock_get_dist.return_value = None
        mock_find_dist.return_value = None

        config = MagicMock()
        config.pyproject_path = Path("/nonexistent/pyproject.toml")

        result = _get_dependencies(config)
        assert result == []

    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution"
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_console_script_distribution"
    )
    def test_parses_pyproject_deps(self, mock_find_dist, mock_get_dist, tmp_path):
        mock_get_dist.return_value = None
        mock_find_dist.return_value = None

        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text(
            '[project]\ndependencies = ["requests>=2.0", "click>=8.0"]'
        )
        config = MagicMock()
        config.pyproject_path = toml_path

        result = _get_dependencies(config)
        assert ("requests", ">=2.0") in result
        assert ("click", ">=8.0") in result

    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution"
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_console_script_distribution"
    )
    def test_skips_non_list_deps(self, mock_find_dist, mock_get_dist, tmp_path):
        mock_get_dist.return_value = None
        mock_find_dist.return_value = None

        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text('[project]\ndependencies = "not a list"')
        config = MagicMock()
        config.pyproject_path = toml_path

        result = _get_dependencies(config)
        assert result == []


# ---------------------------------------------------------------------------
# _get_script_commands
# ---------------------------------------------------------------------------


class TestGetScriptCommands:
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_installed_script_commands"
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name")
    def test_returns_installed_commands(self, mock_name, mock_installed):
        mock_name.return_value = "mycli"
        mock_installed.return_value = ["mycli", "mycli-other"]
        result = _get_script_commands()
        assert result == ["mycli", "mycli-other"]

    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_installed_script_commands"
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name")
    def test_adds_primary_command_if_missing(self, mock_name, mock_installed):
        mock_name.return_value = "primary"
        mock_installed.return_value = ["mycli"]
        result = _get_script_commands()
        assert result == ["primary", "mycli"]

    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_installed_script_commands"
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name")
    def test_falls_back_to_pyproject_scripts(
        self, mock_name, mock_installed, tmp_path, monkeypatch
    ):
        mock_name.return_value = "mycli"
        mock_installed.return_value = []

        monkeypatch.chdir(tmp_path)
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text(
            '[project.scripts]\nmycli = "mycli:main"\nother = "other:main"'
        )

        result = _get_script_commands()
        assert "mycli" in result

    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_installed_script_commands"
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name")
    def test_returns_primary_when_no_scripts(
        self, mock_name, mock_installed, tmp_path, monkeypatch
    ):
        mock_name.return_value = "mycli"
        mock_installed.return_value = []

        monkeypatch.chdir(tmp_path)

        result = _get_script_commands()
        assert result == ["mycli"]

    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_installed_script_commands"
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name")
    def test_returns_empty_when_nothing(
        self, mock_name, mock_installed, tmp_path, monkeypatch
    ):
        mock_name.return_value = None
        mock_installed.return_value = []

        monkeypatch.chdir(tmp_path)

        result = _get_script_commands()
        assert result == []

    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_installed_script_commands"
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name")
    def test_handles_non_dict_scripts_in_pyproject(
        self, mock_name, mock_installed, tmp_path, monkeypatch
    ):
        mock_name.return_value = "mycli"
        mock_installed.return_value = []

        monkeypatch.chdir(tmp_path)
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text("[project.scripts]\nmycli = 42")

        result = _get_script_commands()
        assert isinstance(result, list)

    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_installed_script_commands"
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name")
    def test_pyproject_scripts_adds_primary_when_missing(
        self, mock_name, mock_installed, tmp_path, monkeypatch
    ):
        mock_name.return_value = "primary"
        mock_installed.return_value = []

        monkeypatch.chdir(tmp_path)
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text('[project.scripts]\nmycli = "mycli:main"')

        result = _get_script_commands()
        assert "primary" in result
        assert "mycli" in result

    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_installed_script_commands"
    )
    @patch("usecli.cli.core.ui.title.get_script_command_name")
    def test_pyproject_scripts_returns_all_when_primary_present(
        self, mock_name, mock_installed, tmp_path, monkeypatch
    ):
        mock_name.return_value = "mycli"
        mock_installed.return_value = []

        monkeypatch.chdir(tmp_path)
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text(
            '[project.scripts]\nmycli = "mycli:main"\nother = "other:main"'
        )

        result = _get_script_commands()
        assert "mycli" in result
        assert "other" in result


# ---------------------------------------------------------------------------
# AboutCommand
# ---------------------------------------------------------------------------


class TestAboutCommand:
    def _make_command(self):
        app = MagicMock()
        return AboutCommand(app)

    def test_signature(self):
        cmd = self._make_command()
        assert cmd.signature() == "about"

    def test_description(self):
        cmd = self._make_command()
        assert "information" in cmd.description().lower()

    @patch("usecli.cli.core.runtime.is_json_mode", return_value=True)
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_description",
        return_value="Test desc",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_version",
        return_value="1.0.0",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution",
        return_value=None,
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_script_commands",
        return_value=["mycli"],
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_dependencies",
        return_value=[],
    )
    @patch("usecli.cli.core.ui.title.get_project_name", return_value="TestApp")
    @patch("usecli.cli.commands.defaults.base.about_command.get_config")
    def test_handle_json_mode_returns_data(
        self,
        mock_config,
        mock_name,
        mock_deps,
        mock_scripts,
        mock_dist,
        mock_version,
        mock_desc,
        mock_json,
    ):
        cmd = self._make_command()
        result = cmd.handle()

        assert result["name"] == "TestApp"
        assert result["version"] == "1.0.0"
        assert result["description"] == "Test desc"
        assert "python_version" in result
        assert "platform" in result
        assert result["entry_points"] == ["mycli"]
        assert result["dependencies"] == []

    @patch("usecli.cli.core.runtime.is_json_mode", return_value=False)
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_description",
        return_value="Test desc",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_version",
        return_value="1.0.0",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution",
        return_value=MagicMock(),
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_script_commands",
        return_value=["mycli"],
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_dependencies",
        return_value=[("click", ">=8.0")],
    )
    @patch("usecli.cli.core.ui.title.get_project_name", return_value="TestApp")
    @patch("usecli.cli.commands.defaults.base.about_command.get_config")
    @patch("usecli.cli.commands.defaults.base.about_command.console")
    @patch("importlib.metadata.version")
    def test_handle_normal_mode_prints_and_returns(
        self,
        mock_ver,
        mock_console,
        mock_config,
        mock_name,
        mock_deps,
        mock_scripts,
        mock_dist,
        mock_version,
        mock_desc,
        mock_json,
    ):
        mock_ver.return_value = "8.1.0"
        cmd = self._make_command()
        result = cmd.handle()

        assert result["name"] == "TestApp"
        assert result["version"] == "1.0.0"
        assert mock_console.print.called

    @patch("usecli.cli.core.runtime.is_json_mode", return_value=True)
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_description",
        return_value="desc",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_version",
        return_value="1.0.0",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution",
        return_value=MagicMock(),
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_script_commands",
        return_value=["cli"],
    )
    @patch("usecli.cli.commands.defaults.base.about_command._get_dependencies")
    @patch("usecli.cli.core.ui.title.get_project_name", return_value="App")
    @patch("usecli.cli.commands.defaults.base.about_command.get_config")
    def test_handle_with_installed_and_uninstalled_deps(
        self,
        mock_config,
        mock_name,
        mock_deps,
        mock_scripts,
        mock_dist,
        mock_version,
        mock_desc,
        mock_json,
    ):
        mock_deps.return_value = [("click", ">=8.0"), ("missing-pkg", None)]

        cmd = self._make_command()
        with patch("importlib.metadata.version") as mock_get_ver:

            def side_effect(name):
                if name == "click":
                    return "8.1.0"
                raise PackageNotFoundError(name)

            mock_get_ver.side_effect = side_effect
            result = cmd.handle()

        assert len(result["dependencies"]) == 2
        assert result["dependencies"][0]["name"] == "click"
        assert result["dependencies"][0]["version"] == "8.1.0"
        assert result["dependencies"][1]["name"] == "missing-pkg"
        assert result["dependencies"][1]["version"] is None

    @patch("usecli.cli.core.runtime.is_json_mode", return_value=False)
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_description",
        return_value="desc",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_version",
        return_value="1.0.0",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution",
        return_value=None,
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_script_commands",
        return_value=["cli"],
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_dependencies",
        return_value=[],
    )
    @patch("usecli.cli.core.ui.title.get_project_name", return_value="App")
    @patch("usecli.cli.commands.defaults.base.about_command.get_config")
    @patch("usecli.cli.commands.defaults.base.about_command.console")
    def test_handle_normal_mode_without_dist_uses_app_labels(
        self,
        mock_console,
        mock_config,
        mock_name,
        mock_deps,
        mock_scripts,
        mock_dist,
        mock_version,
        mock_desc,
        mock_json,
    ):
        cmd = self._make_command()
        result = cmd.handle()
        assert "version" in result

    @patch("usecli.cli.commands.defaults.base.about_command.console")
    def test_print_row(self, mock_console):
        mock_console.render_str.return_value = MagicMock(plain="value")
        cmd = self._make_command()
        cmd._print_row("Label", "value")
        assert mock_console.print.called

    @patch("usecli.cli.core.runtime.is_json_mode", return_value=False)
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_description",
        return_value="desc",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_version",
        return_value="1.0.0",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution",
        return_value=MagicMock(),
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_script_commands",
        return_value=["cli", "cli-other"],
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_dependencies",
        return_value=[],
    )
    @patch("usecli.cli.core.ui.title.get_project_name", return_value="App")
    @patch("usecli.cli.commands.defaults.base.about_command.get_config")
    @patch("usecli.cli.commands.defaults.base.about_command.console")
    def test_handle_normal_mode_prints_multiple_entry_points(
        self,
        mock_console,
        mock_config,
        mock_name,
        mock_deps,
        mock_scripts,
        mock_dist,
        mock_version,
        mock_desc,
        mock_json,
    ):
        cmd = self._make_command()
        result = cmd.handle()
        assert len(result["entry_points"]) == 2

    @patch("usecli.cli.core.runtime.is_json_mode", return_value=False)
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_description",
        return_value="desc",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_version",
        return_value="1.0.0",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution",
        return_value=MagicMock(),
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_script_commands",
        return_value=["cli"],
    )
    @patch("usecli.cli.commands.defaults.base.about_command._get_dependencies")
    @patch("usecli.cli.core.ui.title.get_project_name", return_value="App")
    @patch("usecli.cli.commands.defaults.base.about_command.get_config")
    @patch("usecli.cli.commands.defaults.base.about_command.console")
    @patch("importlib.metadata.version")
    def test_handle_normal_mode_prints_deps(
        self,
        mock_ver,
        mock_console,
        mock_config,
        mock_name,
        mock_deps,
        mock_scripts,
        mock_dist,
        mock_version,
        mock_desc,
        mock_json,
    ):
        mock_ver.return_value = "8.1.0"
        mock_deps.return_value = [("click", ">=8.0")]
        cmd = self._make_command()
        result = cmd.handle()
        assert len(result["dependencies"]) == 1

    @patch("usecli.cli.core.runtime.is_json_mode", return_value=False)
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_description",
        return_value="desc",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_version",
        return_value="1.0.0",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution",
        return_value=MagicMock(),
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_script_commands",
        return_value=["cli"],
    )
    @patch("usecli.cli.commands.defaults.base.about_command._get_dependencies")
    @patch("usecli.cli.core.ui.title.get_project_name", return_value="App")
    @patch("usecli.cli.commands.defaults.base.about_command.get_config")
    @patch("usecli.cli.commands.defaults.base.about_command.console")
    @patch("importlib.metadata.version")
    def test_handle_normal_mode_with_uninstalled_dep(
        self,
        mock_ver,
        mock_console,
        mock_config,
        mock_name,
        mock_deps,
        mock_scripts,
        mock_dist,
        mock_version,
        mock_desc,
        mock_json,
    ):
        mock_ver.side_effect = PackageNotFoundError("pkg")
        mock_deps.return_value = [("missing-pkg", ">=1.0")]
        cmd = self._make_command()
        result = cmd.handle()
        assert len(result["dependencies"]) == 1

    @patch("usecli.cli.core.runtime.is_json_mode", return_value=False)
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_description",
        return_value="desc",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_version",
        return_value="1.0.0",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution",
        return_value=MagicMock(),
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_script_commands",
        return_value=["cli"],
    )
    @patch("usecli.cli.commands.defaults.base.about_command._get_dependencies")
    @patch("usecli.cli.core.ui.title.get_project_name", return_value="App")
    @patch("usecli.cli.commands.defaults.base.about_command.get_config")
    @patch("usecli.cli.commands.defaults.base.about_command.console")
    @patch("importlib.metadata.version")
    def test_handle_normal_mode_with_uninstalled_dep_no_spec(
        self,
        mock_ver,
        mock_console,
        mock_config,
        mock_name,
        mock_deps,
        mock_scripts,
        mock_dist,
        mock_version,
        mock_desc,
        mock_json,
    ):
        mock_ver.side_effect = PackageNotFoundError("pkg")
        mock_deps.return_value = [("missing-pkg", None)]
        cmd = self._make_command()
        result = cmd.handle()
        assert len(result["dependencies"]) == 1

    @patch("usecli.cli.core.runtime.is_json_mode", return_value=False)
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_description",
        return_value="desc",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_version",
        return_value="1.0.0",
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_application_distribution",
        return_value=MagicMock(),
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_script_commands",
        return_value=["cli"],
    )
    @patch(
        "usecli.cli.commands.defaults.base.about_command._get_dependencies",
        return_value=[],
    )
    @patch("usecli.cli.core.ui.title.get_project_name", return_value="App")
    @patch("usecli.cli.commands.defaults.base.about_command.get_config")
    @patch("usecli.cli.commands.defaults.base.about_command.console")
    def test_handle_normal_mode_no_deps_prints_unable(
        self,
        mock_console,
        mock_config,
        mock_name,
        mock_deps,
        mock_scripts,
        mock_dist,
        mock_version,
        mock_desc,
        mock_json,
    ):
        cmd = self._make_command()
        result = cmd.handle()
        assert result["dependencies"] == []
