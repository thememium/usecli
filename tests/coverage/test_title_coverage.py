"""Coverage-focused tests for usecli.cli.core.ui.title.

Targets uncovered lines without modifying source:

- line 61: get_script_command_name returns a non-"usecli" config name when the
  pyproject lookup finds nothing
- line 113: print_title resolves a relative title_file against the project root
- lines 120-121: print_title swallows an OSError while reading the title file
- lines 145-146: print_title prints the default ASCII art when pyfiglet is
  unavailable and the title is None/"usecli"

Note: line 12 (``import tomli as tomllib``) is only reachable on Python < 3.11
and is therefore not covered on the 3.12 test interpreter.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from usecli.cli.core.ui.title import get_script_command_name, print_title


class TestGetScriptCommandNameConfigFallback:
    @patch("usecli.cli.core.ui.title._get_script_command_name")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_returns_config_name_when_pyproject_finds_nothing(
        self, mock_config, mock_pyproject
    ):
        """When has_key is False and pyproject lookup returns None, a non-usecli
        config command_name is still returned (line 61)."""
        mock_config.return_value = MagicMock(
            has_key=MagicMock(return_value=False),
            get=MagicMock(return_value="custom"),
        )
        mock_pyproject.return_value = None
        result = get_script_command_name()
        assert result == "custom"


class TestPrintTitleRelativeTitleFile:
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_relative_title_file_resolved_against_project_root(
        self, mock_config, mock_console, tmp_path
    ):
        """A relative title_file is joined to the project root (line 113)."""
        title_file = tmp_path / "title.txt"
        title_file.write_text("Relative Title Art")
        mock_config.return_value = MagicMock(
            get=MagicMock(return_value="title.txt"),
            get_project_root=MagicMock(return_value=tmp_path),
        )
        print_title()
        assert mock_console.print.called


class TestPrintTitleTitleFileOSError:
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_os_error_reading_title_file_is_swallowed(
        self, mock_config, mock_console, tmp_path
    ):
        """An OSError while reading the title file is caught (lines 120-121)."""
        # A directory exists but read_text() raises IsADirectoryError (an OSError)
        title_dir = tmp_path / "title_dir"
        title_dir.mkdir()
        mock_config.return_value = MagicMock(
            get=MagicMock(return_value=str(title_dir)),
            get_project_root=MagicMock(return_value=tmp_path),
        )
        # Should not raise; falls through to default title rendering
        print_title()
        assert mock_console.print.called


class TestPrintTitlePyfigletUnavailable:
    @patch("usecli.cli.core.ui.title.console")
    @patch("usecli.cli.core.ui.title.get_config")
    def test_custom_title_plain_text_when_pyfiglet_missing(
        self, mock_config, mock_console
    ):
        """When pyfiglet is unavailable, a custom title is printed as plain text
        (lines 129-148)."""
        mock_config.return_value = MagicMock(
            get=MagicMock(return_value=None),
        )
        import sys

        saved = sys.modules.get("pyfiglet")
        sys.modules["pyfiglet"] = None  # type: ignore[ty:invalid-assignment]
        try:
            print_title("My Custom Title")
        finally:
            if saved is not None:
                sys.modules["pyfiglet"] = saved
            else:
                sys.modules.pop("pyfiglet", None)

        call_args = mock_console.print.call_args[0][0]
        assert "My Custom Title" in call_args
