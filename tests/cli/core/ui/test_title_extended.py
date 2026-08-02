"""Tests for usecli.cli.core.ui.title — title display and name resolution."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import MagicMock, patch

from usecli.cli.core.ui.title import (
    _get_script_command_name,
    get_project_name,
    get_script_command_name,
    print_title,
)

# ---------------------------------------------------------------------------
# _get_script_command_name
# ---------------------------------------------------------------------------


class TestGetScriptCommandNameInternal:
    def test_returns_name_from_pyproject(self, tmp_path):
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text('[project.scripts]\nmycli = "usecli:main"\n')
        result = _get_script_command_name(tmp_path)
        assert result == "mycli"

    def test_returns_none_when_no_matching_target(self, tmp_path):
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text('[project.scripts]\nother = "other:main"\n')
        result = _get_script_command_name(tmp_path)
        assert result is None

    def test_returns_none_when_no_pyproject(self, tmp_path):
        result = _get_script_command_name(tmp_path)
        assert result is None

    def test_returns_none_when_no_scripts_section(self, tmp_path):
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text('[project]\nname = "test"\n')
        result = _get_script_command_name(tmp_path)
        assert result is None

    def test_defaults_to_cwd(self):
        with patch("usecli.cli.core.ui.title.Path") as mock_path:
            mock_path.cwd.return_value = Path("/nonexistent")
            mock_path.side_effect = lambda *a: Path(*a)
            result = _get_script_command_name()
            assert result is None

    def test_handles_invalid_toml(self, tmp_path):
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text("not = = valid")
        result = _get_script_command_name(tmp_path)
        assert result is None

    def test_returns_none_when_scripts_not_dict(self, tmp_path):
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text('[project]\nscripts = "not a dict"')
        result = _get_script_command_name(tmp_path)
        assert result is None


# ---------------------------------------------------------------------------
# get_script_command_name
# ---------------------------------------------------------------------------


class TestGetScriptCommandName:
    @patch("usecli.cli.core.ui.title.get_config")
    def test_returns_config_command_name(self, mock_config):
        mock_config.return_value = MagicMock(
            has_key=MagicMock(return_value=True),
            get=MagicMock(return_value="mycli"),
        )
        result = get_script_command_name()
        assert result == "mycli"

    @patch("usecli.cli.core.ui.title._get_script_command_name")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_falls_back_to_pyproject(self, mock_config, mock_pyproject):
        mock_config.return_value = MagicMock(
            has_key=MagicMock(return_value=False),
            get=MagicMock(return_value=None),
        )
        mock_pyproject.return_value = "pycli"
        result = get_script_command_name()
        assert result == "pycli"

    @patch("usecli.cli.core.ui.title._get_script_command_name")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_returns_default_when_nothing_found(self, mock_config, mock_pyproject):
        mock_config.return_value = MagicMock(
            has_key=MagicMock(return_value=False),
            get=MagicMock(return_value=None),
        )
        mock_pyproject.return_value = None
        result = get_script_command_name(default="fallback")
        assert result == "fallback"

    @patch("usecli.cli.core.ui.title.get_config")
    def test_returns_config_name_when_not_usecli(self, mock_config):
        mock_config.return_value = MagicMock(
            has_key=MagicMock(return_value=True),
            get=MagicMock(return_value="custom"),
        )
        with patch("usecli.cli.core.ui.title._get_script_command_name", return_value=None):
            result = get_script_command_name()
            assert result == "custom"


# ---------------------------------------------------------------------------
# get_project_name
# ---------------------------------------------------------------------------


class TestGetProjectName:
    @patch("usecli.cli.core.ui.title.get_config")
    def test_returns_config_title(self, mock_config):
        mock_config.return_value = MagicMock(
            has_key=MagicMock(return_value=True),
            get=MagicMock(return_value="My App"),
        )
        result = get_project_name()
        assert result == "My App"

    @patch("usecli.cli.core.ui.title.get_config")
    def test_normalizes_usecli_title(self, mock_config):
        mock_config.return_value = MagicMock(
            has_key=MagicMock(return_value=True),
            get=MagicMock(return_value="usecli"),
        )
        result = get_project_name()
        assert result == "useCli"

    @patch("usecli.cli.core.ui.title._get_script_command_name")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_falls_back_to_pyproject_name(self, mock_config, mock_pyproject):
        mock_config.return_value = MagicMock(
            has_key=MagicMock(return_value=False),
            get=MagicMock(return_value=None),
        )
        mock_pyproject.return_value = "mycli"
        result = get_project_name()
        assert result == "mycli"

    @patch("usecli.cli.core.ui.title.metadata")
    @patch("usecli.cli.core.ui.title._get_script_command_name")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_falls_back_to_metadata(self, mock_config, mock_pyproject, mock_meta):
        mock_config.return_value = MagicMock(
            has_key=MagicMock(return_value=False),
            get=MagicMock(return_value=None),
        )
        mock_pyproject.return_value = None
        mock_meta.return_value = {"Name": "my-package"}
        result = get_project_name()
        assert result == "my-package"

    @patch("usecli.cli.core.ui.title.metadata")
    @patch("usecli.cli.core.ui.title._get_script_command_name")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_returns_usecli_for_usecli_metadata(
        self, mock_config, mock_pyproject, mock_meta
    ):
        mock_config.return_value = MagicMock(
            has_key=MagicMock(return_value=False),
            get=MagicMock(return_value=None),
        )
        mock_pyproject.return_value = None
        mock_meta.return_value = {"Name": "usecli"}
        result = get_project_name()
        assert result == "useCli"

    @patch(
        "usecli.cli.core.ui.title.metadata", side_effect=PackageNotFoundError("usecli")
    )
    @patch("usecli.cli.core.ui.title._get_script_command_name")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_returns_usecli_when_metadata_not_found(
        self, mock_config, mock_pyproject, mock_meta
    ):
        mock_config.return_value = MagicMock(
            has_key=MagicMock(return_value=False),
            get=MagicMock(return_value=None),
        )
        mock_pyproject.return_value = None
        result = get_project_name()
        assert result == "useCli"


# ---------------------------------------------------------------------------
# print_title
# ---------------------------------------------------------------------------


class TestPrintTitle:
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_prints_default_usecli_title(self, mock_config, mock_console):
        mock_config.return_value = MagicMock(
            get=MagicMock(return_value=None),
        )
        print_title()
        assert mock_console.print.called

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_prints_default_when_title_is_usecli(self, mock_config, mock_console):
        mock_config.return_value = MagicMock(
            get=MagicMock(return_value=None),
        )
        print_title("usecli")
        assert mock_console.print.called

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_prints_custom_title_with_pyfiglet(self, mock_config, mock_console):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: None if k == "title_file" else d
            ),
        )
        print_title("My App")
        assert mock_console.print.called

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_prints_title_file(self, mock_config, mock_console, tmp_path):
        title_file = tmp_path / "title.txt"
        title_file.write_text("Custom Title Art")
        mock_config.return_value = MagicMock(
            get=MagicMock(return_value=str(title_file)),
            get_project_root=MagicMock(return_value=tmp_path),
        )
        print_title()
        assert mock_console.print.called

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_handles_os_error_on_title_file(self, mock_config, mock_console):
        mock_config.return_value = MagicMock(
            get=MagicMock(return_value="/nonexistent/title.txt"),
            get_project_root=MagicMock(return_value=Path("/nonexistent")),
        )
        print_title()
        assert mock_console.print.called

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_handles_font_not_found(self, mock_config, mock_console):
        import pyfiglet as real_pyfiglet

        with patch.object(
            real_pyfiglet,
            "figlet_format",
            side_effect=real_pyfiglet.FontNotFound("bad font"),
        ):
            mock_config.return_value = MagicMock(
                get=MagicMock(
                    side_effect=lambda k, d=None: "big" if k == "title_font" else None
                ),
            )
            print_title("My App")
            assert mock_console.print.called

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_handles_import_error_for_pyfiglet(self, mock_config, mock_console):
        mock_config.return_value = MagicMock(
            get=MagicMock(return_value=None),
        )
        import sys
        saved = sys.modules.get("pyfiglet")
        sys.modules["pyfiglet"] = None
        try:
            print_title("My Custom Title")
            assert mock_console.print.called
        finally:
            if saved is not None:
                sys.modules["pyfiglet"] = saved
            else:
                sys.modules.pop("pyfiglet", None)
