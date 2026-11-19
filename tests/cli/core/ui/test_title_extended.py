"""Tests for usecli.cli.core.ui.title — title display and name resolution."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import MagicMock, patch

from usecli.cli.config.colors import COLOR
from usecli.cli.core.ui.title import (
    _get_script_command_name,
    _invoked_script_name,
    _running_framework_distribution,
    get_framework_description,
    get_project_name,
    get_project_version,
    get_script_command_name,
    print_title,
    render_figlet_title,
    render_plain_title,
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
        with patch(
            "usecli.cli.core.ui.title._get_script_command_name", return_value=None
        ):
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
# render_figlet_title
# ---------------------------------------------------------------------------


class TestRenderFigletTitle:
    def test_strips_leading_blank_font_rows(self):
        import pyfiglet

        rendered = render_figlet_title(pyfiglet, "cogrep", "big")

        assert rendered.split("\n")[0].strip()
        assert "___" in rendered


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
                side_effect=lambda k, d=None: None if k == "banner.file" else d
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
    def test_title_file_trailing_newline_does_not_add_blank_line(
        self, mock_config, mock_console, tmp_path
    ):
        title_file = tmp_path / "title.txt"
        title_file.write_text("Custom Title Art\n\n")
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: {
                    "banner.file": str(title_file),
                    "banner.top_space": False,
                    "banner.bottom_space": False,
                }.get(k, d)
            ),
            has_key=MagicMock(return_value=False),
            get_project_root=MagicMock(return_value=tmp_path),
        )

        print_title()

        art = next(
            call.args[0]
            for call in mock_console.print.call_args_list
            if call.args and "Custom Title Art" in call.args[0]
        )
        assert not art.endswith("\n")

    @patch("usecli.cli.core.ui.title.get_project_version", return_value="1.2.3")
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_title_file_renders_description_and_version(
        self, mock_config, mock_console, _mock_version, tmp_path
    ):
        title_file = tmp_path / "title.txt"
        title_file.write_text("Custom Title Art")
        values = {
            "banner.file": str(title_file),
            "banner.show_description": True,
            "banner.show_version": True,
            "banner.top_space": False,
            "banner.bottom_space": False,
            "description": "A demo CLI",
        }
        mock_config.return_value = MagicMock(
            get=MagicMock(side_effect=lambda k, d=None: values.get(k, d)),
            has_key=MagicMock(side_effect=lambda k: k in values),
            get_project_root=MagicMock(return_value=tmp_path),
        )

        print_title("My App")

        printed = [
            call.args[0] for call in mock_console.print.call_args_list if call.args
        ]
        assert any("Custom Title Art" in value for value in printed)
        assert any("v1.2.3" in value for value in printed)
        assert any("A demo CLI" in value for value in printed)

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
                    side_effect=lambda k, d=None: "big" if k == "banner.font" else None
                ),
            )
            print_title("My App")
            assert mock_console.print.called

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_renders_text_when_title_font_not_configured(
        self, mock_config, mock_console
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(return_value=None),
            has_key=MagicMock(return_value=False),
        )
        print_title("My App")
        assert "My App" in mock_console.print.call_args_list[0].args[0]

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_handles_import_error_for_pyfiglet(self, mock_config, mock_console):
        mock_config.return_value = MagicMock(
            get=MagicMock(return_value=None),
        )
        import sys

        saved = sys.modules.get("pyfiglet")
        sys.modules["pyfiglet"] = None  # type: ignore[ty:invalid-assignment]
        try:
            print_title("My Custom Title")
            assert mock_console.print.called
        finally:
            if saved is not None:
                sys.modules["pyfiglet"] = saved
            else:
                sys.modules.pop("pyfiglet", None)

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_prints_relative_title_file(self, mock_config, mock_console, tmp_path):
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
    def test_banner_top_space_adds_leading_blank_in_figlet_mode(
        self, mock_config, mock_console
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: (
                    True
                    if k == "banner.top_space"
                    else ("big" if k == "banner.font" else None)
                )
            ),
        )
        print_title("My App")
        assert mock_console.print.call_args_list[0].args == ()

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_no_leading_blank_in_figlet_mode_by_default(
        self, mock_config, mock_console
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: "big" if k == "banner.font" else None
            ),
        )
        print_title("My App")
        assert mock_console.print.call_args_list[0].args != ()

    @patch("usecli.cli.core.ui.title.get_figlet", return_value=None)
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_banner_top_space_adds_leading_blank_in_plain_mode(
        self, mock_config, mock_console, _mock_figlet
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: True if k == "banner.top_space" else None
            ),
            has_key=MagicMock(return_value=False),
        )
        print_title("My App")
        assert mock_console.print.call_args_list[0].args == ()

    @patch("usecli.cli.core.ui.title.get_figlet", return_value=None)
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_no_leading_blank_in_plain_mode_by_default(
        self, mock_config, mock_console, _mock_figlet
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(return_value=None),
            has_key=MagicMock(return_value=False),
        )
        print_title("My App")
        assert mock_console.print.call_args_list[0].args != ()

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_banner_bottom_space_adds_trailing_blank_in_figlet_mode(
        self, mock_config, mock_console
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: (
                    True
                    if k == "banner.bottom_space"
                    else ("big" if k == "banner.font" else None)
                )
            ),
        )
        print_title("My App")
        assert mock_console.print.call_args_list[-1].args == ()

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_no_trailing_blank_in_figlet_mode_when_disabled(
        self, mock_config, mock_console
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: "big" if k == "banner.font" else None
            ),
        )
        print_title("My App")
        assert mock_console.print.call_args_list[-1].args != ()

    @patch("usecli.cli.core.ui.title.get_figlet", return_value=None)
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_banner_bottom_space_adds_trailing_blank_in_plain_mode(
        self, mock_config, mock_console, _mock_figlet
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: (
                    True if k == "banner.bottom_space" else None
                )
            ),
            has_key=MagicMock(return_value=False),
        )
        print_title("My App")
        assert mock_console.print.call_args_list[-1].args == ()

    @patch("usecli.cli.core.ui.title.get_figlet", return_value=None)
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_no_trailing_blank_in_plain_mode_when_disabled(
        self, mock_config, mock_console, _mock_figlet
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(return_value=None),
            has_key=MagicMock(return_value=False),
        )
        print_title("My App")
        assert mock_console.print.call_args_list[-1].args != ()

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_figlet_shows_description_when_enabled(self, mock_config, mock_console):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: {
                    "banner.font": "big",
                    "banner.show_description": True,
                    "description": "A demo CLI",
                }.get(k, d)
            ),
            has_key=MagicMock(
                side_effect=lambda k: k in {"banner.show_description", "description"}
            ),
        )
        print_title("My App")
        calls = mock_console.print.call_args_list
        description_index = next(
            index
            for index, call in enumerate(calls)
            if call.args and "A demo CLI" in call.args[0]
        )
        assert calls[description_index - 1].args == ()
        assert calls[description_index].args[0].startswith(" ")

    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_figlet_hides_description_by_default(self, mock_config, mock_console):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: {
                    "banner.font": "big",
                    "description": "A demo CLI",
                }.get(k, d)
            ),
            has_key=MagicMock(side_effect=lambda k: k == "description"),
        )
        print_title("My App")
        printed = [
            call.args[0] for call in mock_console.print.call_args_list if call.args
        ]
        assert not any("A demo CLI" in value for value in printed)

    @patch("usecli.cli.core.ui.title.get_figlet", return_value=None)
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_plain_shows_description_by_default(
        self, mock_config, mock_console, _mock_figlet
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: {
                    "description": "A demo CLI",
                }.get(k, d)
            ),
            has_key=MagicMock(side_effect=lambda k: k == "description"),
        )
        print_title("My App")
        printed = [
            call.args[0] for call in mock_console.print.call_args_list if call.args
        ]
        assert any("A demo CLI" in value for value in printed)

    @patch("usecli.cli.core.ui.title.get_figlet", return_value=None)
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_plain_hides_description_when_disabled(
        self, mock_config, mock_console, _mock_figlet
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: {
                    "banner.show_description": False,
                    "description": "A demo CLI",
                }.get(k, d)
            ),
            has_key=MagicMock(
                side_effect=lambda k: k in {"banner.show_description", "description"}
            ),
        )
        print_title("My App")
        printed = [
            call.args[0] for call in mock_console.print.call_args_list if call.args
        ]
        assert not any("A demo CLI" in value for value in printed)

    @patch("usecli.cli.core.ui.title.get_project_version", return_value="1.2.3")
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_figlet_shows_version_when_enabled(
        self, mock_config, mock_console, _mock_version
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: {
                    "banner.font": "big",
                    "banner.show_version": True,
                }.get(k, d)
            ),
            has_key=MagicMock(side_effect=lambda k: k == "banner.show_version"),
        )
        print_title("My App")
        printed = [
            call.args[0] for call in mock_console.print.call_args_list if call.args
        ]
        assert any("v1.2.3" in value for value in printed)

    @patch("usecli.cli.core.ui.title.get_project_version", return_value="1.2.3")
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_figlet_hides_version_by_default(
        self, mock_config, mock_console, mock_version
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: {"banner.font": "big"}.get(k, d)
            ),
            has_key=MagicMock(return_value=False),
        )
        print_title("My App")
        printed = [
            call.args[0] for call in mock_console.print.call_args_list if call.args
        ]
        assert not any("v1.2.3" in value for value in printed)
        mock_version.assert_not_called()

    @patch("usecli.cli.core.ui.title.get_project_version", return_value="1.2.3")
    @patch("usecli.cli.core.ui.title.get_figlet", return_value=None)
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_plain_shows_version_by_default(
        self, mock_config, mock_console, _mock_figlet, _mock_version
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(return_value=None),
            has_key=MagicMock(return_value=False),
        )
        print_title("My App")
        printed = [
            call.args[0] for call in mock_console.print.call_args_list if call.args
        ]
        assert any("v1.2.3" in value for value in printed)

    @patch("usecli.cli.core.ui.title.get_project_version", return_value="1.2.3")
    @patch("usecli.cli.core.ui.title.get_figlet", return_value=None)
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_plain_hides_version_when_disabled(
        self, mock_config, mock_console, _mock_figlet, _mock_version
    ):
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: {"banner.show_version": False}.get(k, d)
            ),
            has_key=MagicMock(side_effect=lambda k: k == "banner.show_version"),
        )
        print_title("My App")
        printed = [
            call.args[0] for call in mock_console.print.call_args_list if call.args
        ]
        assert not any("v1.2.3" in value for value in printed)


# ---------------------------------------------------------------------------
# render_plain_title / get_project_version
# ---------------------------------------------------------------------------


class TestRenderPlainTitle:
    def test_renders_title_version_and_description(self):
        markup = render_plain_title("cogrep", "A custom CLI tool", "v0.1.0")

        first_line, second_line = markup.split("\n")
        assert "cogrep" in first_line
        assert f"[{COLOR.SECONDARY}]v0.1.0[/{COLOR.SECONDARY}]" in first_line
        assert second_line == (
            f"[{COLOR.FOREGROUND_MUTED}]A custom CLI tool[/{COLOR.FOREGROUND_MUTED}]"
        )

    def test_omits_version_and_description_when_missing(self):
        assert render_plain_title("cogrep") == (
            f"[bold {COLOR.PRIMARY}]cogrep[/bold {COLOR.PRIMARY}]"
        )


class TestGetProjectVersion:
    @patch("usecli.cli.core.ui.title.get_config")
    @patch("usecli.cli.core.ui.title.get_script_command_name", return_value=None)
    def test_falls_back_to_project_version(self, mock_command, mock_config):
        mock_config.return_value = MagicMock(
            get_project_version=MagicMock(return_value="2.0.0")
        )

        assert get_project_version() == "2.0.0"

    @patch("usecli.shared.config.manager._find_distribution_for_console_script")
    @patch("usecli.cli.core.ui.title.get_script_command_name", return_value="cogrep")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_unreadable_distribution_version_falls_back(
        self, mock_config, mock_command, mock_find
    ):
        class _BadDist:
            @property
            def version(self):
                raise AttributeError("missing version")

        mock_find.return_value = _BadDist()
        mock_config.return_value = MagicMock(
            get_project_version=MagicMock(return_value="3.1.0")
        )

        assert get_project_version() == "3.1.0"

    @patch("usecli.cli.core.ui.title.get_config")
    @patch("usecli.cli.core.ui.title.get_script_command_name", return_value=None)
    def test_returns_none_when_project_version_unreadable(
        self, mock_command, mock_config
    ):
        mock_config.return_value = MagicMock(
            get_project_version=MagicMock(side_effect=OSError("unreadable"))
        )

        assert get_project_version() is None


# ---------------------------------------------------------------------------
# Framework invocation identity (usecli binary running inside a project)
# ---------------------------------------------------------------------------


def _fake_dist(name: str | None, version: str | None = "0.2.1", summary=None):
    dist = MagicMock()
    dist.metadata = {"Name": name, "Summary": summary}
    dist.version = version
    return dist


class TestInvokedScriptName:
    @patch("usecli.cli.core.ui.title.sys")
    def test_returns_console_script_basename(self, mock_sys):
        mock_sys.argv = ["/usr/local/bin/usecli", "about"]
        assert _invoked_script_name() == "usecli"

    @patch("usecli.cli.core.ui.title.sys")
    def test_empty_argv_returns_none(self, mock_sys):
        mock_sys.argv = []
        assert _invoked_script_name() is None

    @patch("usecli.cli.core.ui.title.sys")
    def test_interpreter_argv0_returns_none(self, mock_sys):
        mock_sys.argv = ["-c"]
        assert _invoked_script_name() is None

    @patch("usecli.cli.core.ui.title.sys")
    def test_empty_basename_returns_none(self, mock_sys):
        mock_sys.argv = ["/usr/local/bin/"]
        assert _invoked_script_name() is None


class TestRunningFrameworkDistribution:
    @patch("usecli.shared.config.manager._find_distribution_for_console_script")
    @patch("usecli.cli.core.ui.title._invoked_script_name", return_value=None)
    def test_without_script_returns_none(self, mock_name, mock_find):
        assert _running_framework_distribution() is None
        mock_find.assert_not_called()

    @patch(
        "usecli.shared.config.manager._find_distribution_for_console_script",
        return_value=None,
    )
    @patch("usecli.cli.core.ui.title._invoked_script_name", return_value="other")
    def test_unknown_script_returns_none(self, mock_name, mock_find):
        assert _running_framework_distribution() is None

    @patch("usecli.shared.config.manager._find_distribution_for_console_script")
    @patch("usecli.cli.core.ui.title._invoked_script_name", return_value="cogrep")
    def test_downstream_script_returns_none(self, mock_name, mock_find):
        mock_find.return_value = _fake_dist("cogrep")
        assert _running_framework_distribution() is None

    @patch("usecli.shared.config.manager._find_distribution_for_console_script")
    @patch("usecli.cli.core.ui.title._invoked_script_name", return_value="usecli")
    def test_framework_script_returns_distribution(self, mock_name, mock_find):
        dist = _fake_dist(" UseCli ")
        mock_find.return_value = dist
        assert _running_framework_distribution() is dist

    @patch("usecli.shared.config.manager._find_distribution_for_console_script")
    @patch("usecli.cli.core.ui.title._invoked_script_name", return_value="usecli")
    def test_distribution_without_name_returns_none(self, mock_name, mock_find):
        mock_find.return_value = _fake_dist(None)
        assert _running_framework_distribution() is None

    @patch("usecli.shared.config.manager._find_distribution_for_console_script")
    @patch("usecli.cli.core.ui.title._invoked_script_name", return_value="usecli")
    def test_distribution_without_metadata_returns_none(self, mock_name, mock_find):
        class _NoMetadata:
            version = "1.0.0"

        mock_find.return_value = _NoMetadata()

        assert _running_framework_distribution() is None


class TestGetFrameworkDescription:
    @patch(
        "usecli.cli.core.ui.title._running_framework_distribution", return_value=None
    )
    def test_downstream_returns_none(self, mock_framework):
        assert get_framework_description() is None

    @patch("usecli.cli.core.ui.title._running_framework_distribution")
    def test_returns_stripped_summary(self, mock_framework):
        mock_framework.return_value = _fake_dist("usecli", summary="  A framework  ")
        assert get_framework_description() == "A framework"

    @patch("usecli.cli.core.ui.title._running_framework_distribution")
    def test_missing_summary_returns_none(self, mock_framework):
        mock_framework.return_value = _fake_dist("usecli", summary=None)
        assert get_framework_description() is None

    @patch("usecli.cli.core.ui.title._running_framework_distribution")
    def test_blank_summary_returns_none(self, mock_framework):
        mock_framework.return_value = _fake_dist("usecli", summary="   ")
        assert get_framework_description() is None


class TestFrameworkIdentity:
    @patch("usecli.cli.core.ui.title._running_framework_distribution")
    def test_script_command_name_is_usecli(self, mock_framework):
        mock_framework.return_value = _fake_dist("usecli")

        assert get_script_command_name(default="cogrep") == "usecli"

    @patch("usecli.cli.core.ui.title._running_framework_distribution")
    def test_project_name_is_usecli(self, mock_framework):
        mock_framework.return_value = _fake_dist("usecli")

        assert get_project_name() == "useCli"

    @patch("usecli.cli.core.ui.title._running_framework_distribution")
    def test_project_version_is_framework_version(self, mock_framework):
        mock_framework.return_value = _fake_dist("usecli", version="0.2.1")

        assert get_project_version() == "0.2.1"

    @patch("usecli.cli.core.ui.title._running_framework_distribution")
    def test_missing_framework_version_returns_none(self, mock_framework):
        class _NoVersion:
            version = None

        mock_framework.return_value = _NoVersion()

        assert get_project_version() is None

    @patch("usecli.cli.core.ui.title._running_framework_distribution")
    def test_unreadable_framework_version_returns_none(self, mock_framework):
        class _BadVersion:
            @property
            def version(self):
                raise OSError("unreadable")

        mock_framework.return_value = _BadVersion()

        assert get_project_version() is None

    @patch("usecli.cli.core.ui.title.get_project_version", return_value="0.2.1")
    @patch("usecli.cli.core.ui.title.get_framework_description")
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_banner_uses_framework_description(
        self, mock_config, mock_console, mock_framework_description, mock_version
    ):
        mock_framework_description.return_value = "A framework summary"
        mock_config.return_value = MagicMock(
            get=MagicMock(
                side_effect=lambda k, d=None: {
                    "banner.show_description": True,
                    "banner.show_version": True,
                    "banner.top_space": False,
                    "banner.bottom_space": False,
                    "description": "Project description",
                }.get(k, d)
            ),
            has_key=MagicMock(
                side_effect=lambda k: (
                    k
                    in {"banner.show_description", "banner.show_version", "description"}
                )
            ),
        )

        print_title("cogrep")

        printed = " ".join(
            str(call.args[0]) for call in mock_console.print.call_args_list if call.args
        )
        assert "A framework summary" in printed
        assert "Project description" not in printed
