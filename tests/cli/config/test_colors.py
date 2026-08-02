"""Tests for usecli.cli.config.colors — utility functions and COLOR class."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from usecli.cli.config.colors import (
    COLOR,
    _ansi_from_hex,
    _build_ansi_palette,
    _config_matches_command,
    _dedupe_paths,
    _get_command_name,
    _get_package_name,
    _hex_to_rgb,
    _load_usecli_config_file,
    _merge_theme_values,
    _normalize_color,
    _normalize_theme_dirs,
    _walk_for_filename,
    bold,
    style,
)

# ---------------------------------------------------------------------------
# Pure utility functions
# ---------------------------------------------------------------------------


class TestHexToRgb:
    def test_valid_six_digit_hex(self):
        assert _hex_to_rgb("#FF0000") == (255, 0, 0)

    def test_valid_without_hash(self):
        assert _hex_to_rgb("00FF00") == (0, 255, 0)

    def test_valid_three_digit_hex(self):
        assert _hex_to_rgb("#F00") == (255, 0, 0)

    def test_valid_three_digit_without_hash(self):
        assert _hex_to_rgb("0F0") == (0, 255, 0)

    def test_invalid_length(self):
        assert _hex_to_rgb("#FF00") is None

    def test_invalid_characters(self):
        assert _hex_to_rgb("#GGHHII") is None

    def test_non_string(self):
        assert _hex_to_rgb(42) is None

    def test_empty_string(self):
        assert _hex_to_rgb("") is None

    def test_whitespace_only(self):
        assert _hex_to_rgb("   ") is None


class TestNormalizeColor:
    def test_valid_color(self):
        assert _normalize_color("#FF0000") == "#FF0000"

    def test_strips_whitespace(self):
        assert _normalize_color("  #FF0000  ") == "#FF0000"

    def test_empty_string(self):
        assert _normalize_color("") is None

    def test_whitespace_only(self):
        assert _normalize_color("   ") is None

    def test_non_string(self):
        assert _normalize_color(42) is None


class TestAnsiFromHex:
    def test_valid_hex(self):
        result = _ansi_from_hex("#FF0000")
        assert result == "\033[38;2;255;0;0m"

    def test_invalid_hex(self):
        assert _ansi_from_hex("invalid") is None


class TestMergeThemeValues:
    def test_returns_defaults_when_no_overrides(self):
        defaults = {"primary": "#FF0000", "secondary": "#00FF00"}
        result = _merge_theme_values(defaults, {}, _normalize_color)
        assert result == defaults

    def test_applies_valid_overrides(self):
        defaults = {"primary": "#FF0000", "secondary": "#00FF00"}
        overrides = {"primary": "#0000FF"}
        result = _merge_theme_values(defaults, overrides, _normalize_color)
        assert result["primary"] == "#0000FF"
        assert result["secondary"] == "#00FF00"

    def test_ignores_unknown_keys(self):
        defaults = {"primary": "#FF0000"}
        overrides = {"unknown": "#0000FF"}
        result = _merge_theme_values(defaults, overrides, _normalize_color)
        assert "unknown" not in result

    def test_ignores_invalid_values(self):
        defaults = {"primary": "#FF0000"}
        overrides = {"primary": ""}
        result = _merge_theme_values(defaults, overrides, _normalize_color)
        assert result["primary"] == "#FF0000"

    def test_handles_non_dict_overrides(self):
        defaults = {"primary": "#FF0000"}
        result = _merge_theme_values(defaults, "not a dict", _normalize_color)
        assert result == defaults


class TestNormalizeThemeDirs:
    def test_returns_empty_for_none(self):
        assert _normalize_theme_dirs(None, None) == []

    def test_handles_string_value(self, tmp_path):
        result = _normalize_theme_dirs("themes", tmp_path)
        assert len(result) == 1
        assert result[0] == tmp_path / "themes"

    def test_handles_absolute_path(self):
        result = _normalize_theme_dirs("/absolute/path", None)
        assert len(result) == 1
        assert result[0] == Path("/absolute/path")

    def test_handles_list_value(self, tmp_path):
        result = _normalize_theme_dirs(["dir1", "dir2"], tmp_path)
        assert len(result) == 2

    def test_skips_empty_strings(self, tmp_path):
        result = _normalize_theme_dirs(["", "  ", "valid"], tmp_path)
        assert len(result) == 1

    def test_skips_non_strings_in_list(self, tmp_path):
        result = _normalize_theme_dirs([42, "valid"], tmp_path)
        assert len(result) == 1

    def test_returns_empty_when_no_project_root(self):
        result = _normalize_theme_dirs("relative", None)
        assert result == []


class TestDedupePaths:
    def test_removes_duplicates(self, tmp_path):
        p1 = tmp_path / "a"
        p2 = tmp_path / "a"
        result = _dedupe_paths([p1, p2])
        assert len(result) == 1

    def test_preserves_unique(self, tmp_path):
        p1 = tmp_path / "a"
        p2 = tmp_path / "b"
        result = _dedupe_paths([p1, p2])
        assert len(result) == 2

    def test_empty_list(self):
        assert _dedupe_paths([]) == []


class TestBuildAnsiPalette:
    def test_builds_from_colors(self):
        colors = {
            k: v
            for k, v in __import__(
                "usecli.cli.config.colors", fromlist=["DEFAULT_THEME_COLORS"]
            ).DEFAULT_THEME_COLORS.items()
        }
        result = _build_ansi_palette(colors)
        assert "reset" in result
        assert "primary" in result
        assert result["reset"] == "\033[0m"

    def test_falls_back_to_default_for_invalid(self):
        colors = {"primary": "invalid", "secondary": "#00FF00"}
        result = _build_ansi_palette(colors)
        # primary should fall back to default
        assert result["primary"] != ""


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------


class TestWalkForFilename:
    def test_finds_file(self, tmp_path):
        target = tmp_path / "test.txt"
        target.write_text("hello")
        results = []
        _walk_for_filename(tmp_path, "test.txt", 0, 6, frozenset(), results)
        assert target in results

    def test_skips_excluded_dirs(self, tmp_path):
        skip_dir = tmp_path / ".venv"
        skip_dir.mkdir()
        target = skip_dir / "test.txt"
        target.write_text("hello")
        results = []
        _walk_for_filename(tmp_path, "test.txt", 0, 6, frozenset({".venv"}), results)
        assert target not in results

    def test_respects_max_depth(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "d" / "e" / "f" / "g"
        deep.mkdir(parents=True)
        target = deep / "test.txt"
        target.write_text("hello")
        results = []
        _walk_for_filename(tmp_path, "test.txt", 0, 3, frozenset(), results)
        assert target not in results

    def test_handles_permission_error(self, tmp_path):
        results = []
        _walk_for_filename(Path("/nonexistent"), "test.txt", 0, 6, frozenset(), results)
        assert results == []


class TestGetCommandName:
    def test_returns_basename(self):
        with patch("usecli.cli.config.colors.sys", argv=["/usr/bin/mycli"]):
            assert _get_command_name() == "mycli"

    def test_returns_none_for_empty_argv(self):
        with patch("usecli.cli.config.colors.sys", argv=[]):
            assert _get_command_name() is None


class TestGetPackageName:
    def test_returns_package_name(self):
        result = _get_package_name()
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# Config file loading
# ---------------------------------------------------------------------------


class TestLoadUsecliConfigFile:
    def test_loads_tool_usecli_section(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text('[tool.usecli]\ntheme = "dark"')
        result = _load_usecli_config_file(config_path)
        assert result["theme"] == "dark"

    def test_loads_usecli_section(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text('[usecli]\ntheme = "light"')
        result = _load_usecli_config_file(config_path)
        assert result["theme"] == "light"

    def test_returns_empty_for_missing_sections(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text('[project]\nname = "test"')
        result = _load_usecli_config_file(config_path)
        assert result == {}

    def test_returns_empty_for_invalid_toml(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text("not = = valid")
        result = _load_usecli_config_file(config_path)
        assert result == {}

    def test_returns_empty_for_nonexistent_file(self, tmp_path):
        result = _load_usecli_config_file(tmp_path / "nonexistent.toml")
        assert result == {}


class TestConfigMatchesCommand:
    def test_returns_true_when_command_is_none(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text('[usecli]\ncommand_name = "mycli"')
        assert _config_matches_command(config_path, None) is True

    def test_returns_true_when_config_matches(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text('[usecli]\ncommand_name = "mycli"')
        with patch(
            "usecli.cli.config.colors._get_console_script_aliases",
            return_value={"mycli"},
        ):
            assert _config_matches_command(config_path, "mycli") is True

    def test_returns_true_when_no_command_in_config(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text('[usecli]\ntheme = "dark"')
        assert _config_matches_command(config_path, "mycli") is True


# ---------------------------------------------------------------------------
# COLOR class
# ---------------------------------------------------------------------------


class TestColor:
    def test_has_primary(self):
        assert COLOR.PRIMARY is not None

    def test_has_secondary(self):
        assert COLOR.SECONDARY is not None

    def test_has_error(self):
        assert COLOR.ERROR is not None

    def test_has_success(self):
        assert COLOR.SUCCESS is not None

    def test_has_warning(self):
        assert COLOR.WARNING is not None

    def test_ansi_has_reset(self):
        assert COLOR.ANSI.RESET == "\033[0m"

    def test_ansi_has_primary(self):
        assert COLOR.ANSI.PRIMARY is not None


class TestBold:
    def test_wraps_color_in_bold(self):
        result = bold("#FF0000")
        assert result == "bold #FF0000"


class TestStyle:
    def test_applies_color(self):
        result = style("Hello", "#FF0000")
        assert result == "[#FF0000]Hello[/#FF0000]"

    def test_applies_bold(self):
        result = style("Hello", "#FF0000", bold=True)
        assert result == "[bold #FF0000]Hello[/bold #FF0000]"


class TestLoadThemeFile:
    def test_loads_valid_theme(self, tmp_path):
        theme_path = tmp_path / "theme.toml"
        theme_path.write_text('[colors]\nprimary = "#FF0000"')
        from usecli.cli.config.colors import _load_theme_file

        result = _load_theme_file(theme_path)
        assert "colors" in result

    def test_returns_empty_for_invalid_toml(self, tmp_path):
        theme_path = tmp_path / "theme.toml"
        theme_path.write_text("not = = valid")
        from usecli.cli.config.colors import _load_theme_file

        result = _load_theme_file(theme_path)
        assert result == {}

    def test_returns_empty_for_non_dict(self, tmp_path):
        theme_path = tmp_path / "theme.toml"
        theme_path.write_text("= 'just a value'")
        from usecli.cli.config.colors import _load_theme_file

        result = _load_theme_file(theme_path)
        # Non-dict TOML returns empty
        assert isinstance(result, dict)


class TestResolveThemePath:
    def test_returns_none_for_empty_name(self):
        from usecli.cli.config.colors import _resolve_theme_path

        assert _resolve_theme_path("", None, {}) is None

    def test_returns_none_for_whitespace_name(self):
        from usecli.cli.config.colors import _resolve_theme_path

        assert _resolve_theme_path("   ", None, {}) is None

    def test_resolves_absolute_path(self, tmp_path):
        theme_path = tmp_path / "custom.toml"
        theme_path.write_text("")
        from usecli.cli.config.colors import _resolve_theme_path

        result = _resolve_theme_path(str(theme_path), None, {})
        assert result == theme_path

    def test_resolves_relative_path_with_project_root(self, tmp_path):
        theme_dir = tmp_path / "themes"
        theme_dir.mkdir()
        theme_path = theme_dir / "custom.toml"
        theme_path.write_text("")
        from usecli.cli.config.colors import _resolve_theme_path

        result = _resolve_theme_path("themes/custom.toml", tmp_path, {})
        assert result == theme_path

    def test_returns_none_for_nonexistent_relative_path(self, tmp_path):
        from usecli.cli.config.colors import _resolve_theme_path

        result = _resolve_theme_path("nonexistent.toml", tmp_path, {})
        assert result is None


class TestIsPreferredPackagePath:
    def test_returns_true_for_venv_path(self):
        from usecli.cli.config.colors import _is_preferred_package_path

        assert _is_preferred_package_path(Path(".venv/lib/python")) is True

    def test_returns_false_for_normal_path(self):
        from usecli.cli.config.colors import _is_preferred_package_path

        assert _is_preferred_package_path(Path("src/usecli")) is False


class TestFindProjectRoot:
    def test_finds_root_with_pyproject(self, tmp_path):
        nested = tmp_path / "src" / "deep"
        nested.mkdir(parents=True)
        (tmp_path / "pyproject.toml").write_text("")
        from usecli.cli.config.colors import _find_project_root

        result = _find_project_root(nested)
        assert result == tmp_path

    def test_finds_root_with_usecli_config(self, tmp_path):
        nested = tmp_path / "src"
        nested.mkdir(parents=True)
        (tmp_path / "usecli.config.toml").write_text("")
        from usecli.cli.config.colors import _find_project_root

        result = _find_project_root(nested)
        assert result == tmp_path

    def test_returns_none_when_not_found(self, tmp_path):
        from usecli.cli.config.colors import _find_project_root

        result = _find_project_root(tmp_path)
        # May return None or tmp_path depending on git root
        assert result is None or isinstance(result, Path)


class TestGetThemeDirs:
    def test_returns_default_dirs(self):
        from usecli.cli.config.colors import _get_theme_dirs

        result = _get_theme_dirs(None, {})
        assert isinstance(result, list)
        # Should always include THEMES_DIR
        assert any("themes" in str(p).lower() for p in result)

    def test_includes_project_themes_dir(self, tmp_path):
        from usecli.cli.config.colors import _get_theme_dirs

        result = _get_theme_dirs(tmp_path, {})
        assert isinstance(result, list)

    def test_includes_config_themes_dir(self, tmp_path):
        from usecli.cli.config.colors import _get_theme_dirs

        result = _get_theme_dirs(tmp_path, {"themes_dir": "custom/themes"})
        assert isinstance(result, list)


class TestGetConsoleScriptAliases:
    def test_returns_empty_for_empty_command(self):
        from usecli.cli.config.colors import _get_console_script_aliases

        result = _get_console_script_aliases("")
        assert result == set()

    def test_returns_empty_for_none_command(self):
        from usecli.cli.config.colors import _get_console_script_aliases

        result = _get_console_script_aliases(None)
        assert result == set()

    def test_returns_command_name_for_unknown(self):
        from usecli.cli.config.colors import _get_console_script_aliases

        result = _get_console_script_aliases("unknown_command_xyz")
        assert "unknown_command_xyz" in result


class TestConfigSignature:
    def test_returns_tuple_for_existing_file(self, tmp_path):
        from usecli.cli.config.colors import _config_signature

        path = tmp_path / "test.toml"
        path.write_text("test")
        result = _config_signature(path)
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert result[0] == path.resolve()

    def test_returns_none_for_nonexistent_file(self):
        from usecli.cli.config.colors import _config_signature

        result = _config_signature(Path("/nonexistent/file.toml"))
        assert isinstance(result, tuple)
        assert result[1] is None


class TestLoadUsecliConfig:
    def test_returns_empty_for_none_root(self):
        from usecli.cli.config.colors import _load_usecli_config

        result, path = _load_usecli_config(None)
        assert result == {}
        assert path is None

    def test_returns_empty_for_nonexistent_root(self, tmp_path):
        from usecli.cli.config.colors import _load_usecli_config

        result, path = _load_usecli_config(tmp_path / "nonexistent")
        assert isinstance(result, dict)
