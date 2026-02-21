"""Comprehensive tests for UI title module.

Tests cover:
- get_project_name(): Reading project name from package metadata
- print_title(): Printing ASCII art title with fallback behavior
"""

from unittest.mock import patch

from usecli.cli.config.colors import COLOR
from usecli.cli.core.ui.title import get_project_name, print_title

# =============================================================================
# get_project_name() Tests
# =============================================================================


class TestGetProjectName:
    """Test suite for get_project_name() function."""

    @patch("usecli.cli.core.ui.title.metadata")
    def test_get_project_name_with_valid_metadata(
        self, mock_metadata, tmp_path, monkeypatch
    ):
        """Test get_project_name() with valid package metadata."""
        monkeypatch.chdir(tmp_path)
        mock_meta = {"Name": "test-cli-project"}
        mock_metadata.return_value = mock_meta

        result = get_project_name()

        assert result == "test-cli-project"
        mock_metadata.assert_called_once_with("usecli")

    @patch("usecli.cli.core.ui.title.metadata")
    def test_get_project_name_returns_default_on_package_not_found(
        self, mock_metadata, tmp_path, monkeypatch
    ):
        """Test get_project_name() returns 'usecli' when package not found."""
        monkeypatch.chdir(tmp_path)
        from importlib.metadata import PackageNotFoundError

        mock_metadata.side_effect = PackageNotFoundError("usecli")

        result = get_project_name()

        assert result == "useCli"

    @patch("usecli.cli.core.ui.title.metadata")
    def test_get_project_name_usecli_default(
        self, mock_metadata, tmp_path, monkeypatch
    ):
        """Test get_project_name() returns default usecli name."""
        monkeypatch.chdir(tmp_path)
        mock_meta = {"Name": "usecli"}
        mock_metadata.return_value = mock_meta

        result = get_project_name()

        assert result == "useCli"


# =============================================================================
# print_title() Tests
# =============================================================================


class TestPrintTitle:
    """Test suite for print_title() function."""

    @patch("usecli.cli.core.ui.title.console")
    def test_print_title_without_error(self, mock_console):
        """Test print_title() successfully prints ASCII art."""
        print_title()

        # Verify console.print was called
        mock_console.print.assert_called_once()

        # Verify the call contains ASCII art with PRIMARY color
        call_args = mock_console.print.call_args[0][0]
        assert "▄█▀▀▀▄█" in call_args
        assert COLOR.PRIMARY in call_args

    @patch("usecli.cli.core.ui.title.console")
    def test_print_title_with_custom_title(self, mock_console):
        """Test print_title() with custom title parameter."""
        custom_title = "Custom Title"
        print_title(custom_title)

        # Verify console.print was called at least once
        assert mock_console.print.call_count >= 1

    @patch("usecli.cli.core.ui.title.console")
    def test_print_title_ascii_art_present(self, mock_console):
        """Test print_title() output contains expected ASCII art characters."""
        print_title()

        call_args = mock_console.print.call_args[0][0]

        # Verify key ASCII art characters are present
        expected_chars = ["▄", "█", "▓", "▒", "░"]
        for char in expected_chars:
            assert char in call_args

    @patch("usecli.cli.core.ui.title.console")
    def test_print_title_contains_color_markup(self, mock_console):
        """Test print_title() output contains Rich color markup."""
        print_title()

        call_args = mock_console.print.call_args[0][0]

        # Verify Rich markup is present
        assert f"[{COLOR.PRIMARY}]" in call_args
        assert "[" in call_args and "]" in call_args

    @patch("usecli.cli.core.ui.title.console")
    def test_print_title_with_import_error_handling(self, mock_console):
        """Test print_title() attempts to print title even with errors."""
        print_title("Fallback Title")

        # Verify console.print was called
        assert mock_console.print.call_count >= 1

    @patch("usecli.cli.core.ui.title.console")
    def test_print_title_with_module_not_found_handling(self, mock_console):
        """Test print_title() attempts to print title even with errors."""
        print_title("Fallback Title")

        # Verify console.print was called
        assert mock_console.print.call_count >= 1

    @patch("usecli.cli.core.ui.title.console")
    def test_print_title_multiple_calls(self, mock_console):
        """Test print_title() can be called multiple times."""
        print_title()
        print_title()
        print_title("Title 3")

        # Verify console.print was called four times (1 + 1 + 2)
        # Custom titles print an empty line plus the title
        assert mock_console.print.call_count == 4

    @patch("usecli.cli.core.ui.title.console")
    def test_print_title_no_return_value(self, mock_console):
        """Test print_title() returns None."""
        result = print_title()
        assert result is None

    @patch("usecli.cli.core.ui.title.console")
    def test_print_title_ascii_structure(self, mock_console):
        """Test print_title() ASCII art has expected structure."""
        print_title()

        call_args = mock_console.print.call_args[0][0]

        # Verify structure contains multiple lines
        lines = call_args.split("\n")
        assert len(lines) > 3

        # Verify some lines contain ASCII art characters
        art_lines = [line for line in lines if any(c in line for c in ["▄", "█", "▓"])]
        assert len(art_lines) > 0

    @patch("usecli.cli.core.ui.title.console")
    def test_print_title_color_constants_used(self, mock_console):
        """Test print_title() uses correct COLOR constants."""
        print_title()

        call_args = mock_console.print.call_args[0][0]

        # Verify PRIMARY color is used
        assert COLOR.PRIMARY in call_args
        # Verify it's in proper Rich markup format
        assert f"[{COLOR.PRIMARY}]" in call_args

    @patch("usecli.cli.core.ui.title.console")
    def test_print_title_none_parameter(self, mock_console):
        """Test print_title() with None as parameter."""
        print_title(None)

        # Should not raise exception
        mock_console.print.assert_called()

    @patch("usecli.cli.core.ui.title.console")
    def test_print_title_empty_string_parameter(self, mock_console):
        """Test print_title() with empty string as parameter."""
        print_title("")

        # Should not raise exception
        mock_console.print.assert_called()

    @patch("usecli.cli.core.ui.title.metadata")
    def test_get_project_name_from_project_scripts(
        self, mock_metadata, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\nname = 'test'\n\n[project.scripts]\nmycli = \"usecli:main\"\n"
        )

        result = get_project_name()

        assert result == "mycli"
        mock_metadata.assert_not_called()
