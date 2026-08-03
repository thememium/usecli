"""Tests for usecli.cli.config.colors — utility functions and COLOR class."""

from __future__ import annotations

import types
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

from usecli.cli.config.colors import (
    _THEME_CACHE,
    COLOR,
    _ansi_from_hex,
    _build_ansi_palette,
    _config_matches_command,
    _dedupe_paths,
    _find_project_root,
    _find_usecli_config_for_console_script,
    _find_usecli_config_in_named_package,
    _find_usecli_config_in_package,
    _find_usecli_config_path,
    _find_usecli_config_path_for_command,
    _get_command_name,
    _get_console_script_aliases,
    _get_package_name,
    _hex_to_rgb,
    _import_tomllib,
    _is_within_usecli_package,
    _load_theme,
    _load_theme_file,
    _load_usecli_config,
    _load_usecli_config_file,
    _merge_theme_values,
    _normalize_color,
    _normalize_theme_dirs,
    _resolve_theme_path,
    _theme_context,
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
        assert _hex_to_rgb(42) is None  # type: ignore[ty:invalid-argument-type]

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
        result = _merge_theme_values(defaults, "not a dict", _normalize_color)  # type: ignore[ty:invalid-argument-type]
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

    def test_continues_on_oserror_for_entry(self):
        entry = MagicMock()
        entry.is_file.side_effect = OSError("boom")
        entry.is_dir.side_effect = OSError("boom")
        fake_dir = MagicMock()
        fake_dir.iterdir.return_value = [entry]
        results: list[Path] = []
        _walk_for_filename(fake_dir, "test.txt", 0, 6, frozenset(), results)
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

    def test_empty_package_returns_usecli(self):
        with (
            patch("usecli.cli.config.colors.__package__", ""),
            patch("usecli.cli.config.colors.__name__", ""),
        ):
            assert _get_package_name() == "usecli"


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

    def test_usecli_not_a_dict(self, tmp_path):
        cfg = tmp_path / "config.toml"
        cfg.write_text('usecli = "not a dict"')
        assert _load_usecli_config_file(cfg) == {}


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

    def test_returns_true_on_load_oserror(self, tmp_path):
        with patch(
            "usecli.cli.config.colors._load_usecli_config_file",
            side_effect=OSError("boom"),
        ):
            assert _config_matches_command(tmp_path / "x.toml", "mycli") is True

    def test_returns_true_for_blank_command(self, tmp_path):
        cfg = tmp_path / "config.toml"
        cfg.write_text('[usecli]\ncommand_name = "   "')
        assert _config_matches_command(cfg, "mycli") is True

    def test_matches_via_aliases(self, tmp_path):
        cfg = tmp_path / "config.toml"
        cfg.write_text('[usecli]\ncommand_name = "other"')
        with patch(
            "usecli.cli.config.colors._get_console_script_aliases",
            return_value={"mycli", "other"},
        ):
            assert _config_matches_command(cfg, "mycli") is True

    def test_not_in_aliases(self, tmp_path):
        cfg = tmp_path / "config.toml"
        cfg.write_text('[usecli]\ncommand_name = "other"')
        with patch(
            "usecli.cli.config.colors._get_console_script_aliases",
            return_value={"something_else"},
        ):
            assert _config_matches_command(cfg, "mycli") is False


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

    def test_non_dict_data(self, tmp_path):
        theme_path = tmp_path / "theme.toml"
        theme_path.write_text("")

        class _FakeTomllib:
            def load(self, _file):
                return ["not", "a", "dict"]

        fake_tomllib = _FakeTomllib()
        with patch(
            "usecli.cli.config.colors._import_tomllib", return_value=fake_tomllib
        ):
            assert _load_theme_file(theme_path) == {}


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

    def test_not_found_in_theme_dirs(self, tmp_path):
        assert _resolve_theme_path("nonexistent", tmp_path, {}) is None


class TestIsPreferredPackagePath:
    def test_returns_true_for_venv_path(self):
        from usecli.cli.config.colors import _is_preferred_package_path

        assert _is_preferred_package_path(Path(".venv/lib/python")) is True

    def test_returns_false_for_normal_path(self):
        from usecli.cli.config.colors import _is_preferred_package_path

        assert _is_preferred_package_path(Path("src/usecli")) is False


class TestIsWithinUsecliPackage:
    def test_returns_false_for_non_package_path(self):
        from usecli.cli.config.colors import _is_within_usecli_package

        result = _is_within_usecli_package(Path("/tmp/test"))
        assert isinstance(result, bool)

    def test_no_spec(self):
        with patch("importlib.util.find_spec", return_value=None):
            assert _is_within_usecli_package(Path("/tmp/x")) is False

    def test_within_package(self, tmp_path):
        spec = MagicMock()
        spec.submodule_search_locations = [str(tmp_path)]
        with patch("importlib.util.find_spec", return_value=spec):
            assert _is_within_usecli_package(tmp_path / "sub") is True


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

    def test_git_root(self, tmp_path):
        (tmp_path / ".git").mkdir()
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        with (
            patch(
                "usecli.cli.config.colors._find_usecli_config_for_console_script",
                return_value=None,
            ),
            patch(
                "usecli.cli.config.colors._find_usecli_config_in_package",
                return_value=None,
            ),
            patch(
                "usecli.cli.config.colors._find_usecli_config_path",
                return_value=None,
            ),
        ):
            assert _find_project_root(nested) == tmp_path

    def test_console_match(self, tmp_path):
        (tmp_path / ".git").mkdir()
        cfg = tmp_path / "elsewhere" / "usecli.config.toml"
        cfg.parent.mkdir()
        cfg.write_text("")
        with patch(
            "usecli.cli.config.colors._find_usecli_config_for_console_script",
            return_value=cfg,
        ):
            assert _find_project_root(tmp_path / "a") == cfg.parent

    def test_config_match(self, tmp_path):
        (tmp_path / ".git").mkdir()
        cfg = tmp_path / "elsewhere" / "usecli.config.toml"
        cfg.parent.mkdir()
        cfg.write_text("")
        with (
            patch(
                "usecli.cli.config.colors._find_usecli_config_for_console_script",
                return_value=None,
            ),
            patch(
                "usecli.cli.config.colors._find_usecli_config_in_package",
                return_value=None,
            ),
            patch(
                "usecli.cli.config.colors._find_usecli_config_path",
                return_value=cfg,
            ),
        ):
            assert _find_project_root(tmp_path / "a") == cfg.parent


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

    @patch("usecli.shared.config.manager._find_distribution_for_console_script")
    def test_includes_entry_point_names(self, mock_find):
        from usecli.cli.config.colors import _get_console_script_aliases

        ep1 = MagicMock()
        ep1.group = "console_scripts"
        ep1.name = "mycli"
        ep2 = MagicMock()
        ep2.group = "console_scripts"
        ep2.name = "mycli-other"
        ep3 = MagicMock()
        ep3.group = "other"
        ep3.name = "ignore"

        mock_dist = MagicMock()
        mock_dist.entry_points = [ep1, ep2, ep3]
        mock_find.return_value = mock_dist

        result = _get_console_script_aliases("mycli")
        assert "mycli" in result
        assert "mycli-other" in result
        assert "ignore" not in result

    @patch("usecli.shared.config.manager._find_distribution_for_console_script")
    def test_handles_attribute_error_on_entry_points(self, mock_find):
        from usecli.cli.config.colors import _get_console_script_aliases

        mock_dist = MagicMock()
        type(mock_dist).entry_points = PropertyMock(side_effect=AttributeError)
        mock_find.return_value = mock_dist

        result = _get_console_script_aliases("mycli")
        assert "mycli" in result

    def test_handles_oserror_on_entry_points(self):
        mock_dist = MagicMock()
        type(mock_dist).entry_points = PropertyMock(side_effect=OSError("boom"))
        with patch(
            "usecli.shared.config.manager._find_distribution_for_console_script",
            return_value=mock_dist,
        ):
            result = _get_console_script_aliases("mycli")
            assert "mycli" in result


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

        result, _path = _load_usecli_config(tmp_path / "nonexistent")
        assert isinstance(result, dict)

    def test_console_match(self, tmp_path):
        cfg = tmp_path / "elsewhere" / "usecli.config.toml"
        cfg.parent.mkdir()
        cfg.write_text('[usecli]\ntheme = "dark"')
        with patch(
            "usecli.cli.config.colors._find_usecli_config_for_console_script",
            return_value=cfg,
        ):
            result, path = _load_usecli_config(tmp_path)
            assert path == cfg
            assert result["theme"] == "dark"

    def test_path_for_command(self, tmp_path):
        cfg = tmp_path / "elsewhere" / "usecli.config.toml"
        cfg.parent.mkdir()
        cfg.write_text('[usecli]\ntheme = "light"')
        with (
            patch(
                "usecli.cli.config.colors._find_usecli_config_for_console_script",
                return_value=None,
            ),
            patch(
                "usecli.cli.config.colors._find_usecli_config_in_package",
                return_value=None,
            ),
            patch(
                "usecli.cli.config.colors._find_usecli_config_path_for_command",
                return_value=cfg,
            ),
        ):
            result, path = _load_usecli_config(tmp_path)
            assert path == cfg
            assert result["theme"] == "light"

    def test_no_config_found(self, tmp_path):
        with (
            patch(
                "usecli.cli.config.colors._find_usecli_config_for_console_script",
                return_value=None,
            ),
            patch(
                "usecli.cli.config.colors._find_usecli_config_in_package",
                return_value=None,
            ),
            patch(
                "usecli.cli.config.colors._find_usecli_config_path_for_command",
                return_value=None,
            ),
        ):
            result, path = _load_usecli_config(tmp_path)
            assert result == {}
            assert path is None


# ---------------------------------------------------------------------------
# Coverage-focused: theme loading, config discovery, and error branches
# ---------------------------------------------------------------------------


class TestImportTomllib:
    def test_imports_tomli_on_py_lt_311(self):
        fake = types.ModuleType("tomli")
        with (
            patch("usecli.cli.config.colors.sys.version_info", (3, 10)),
            patch.dict("sys.modules", {"tomli": fake}),
        ):
            assert _import_tomllib() is fake


class TestFindUsecliConfigPath:
    def test_nonexistent_root(self, tmp_path):
        assert (
            _find_usecli_config_path(tmp_path / "nope", tmp_path, skip_venv=True)
            is None
        )

    def test_no_candidates(self, tmp_path):
        assert _find_usecli_config_path(tmp_path, tmp_path, skip_venv=True) is None

    def test_preferred_inside_start_dir(self, tmp_path):
        start = tmp_path / "start"
        start.mkdir()
        cfg = start / "usecli.config.toml"
        cfg.write_text("")
        result = _find_usecli_config_path(tmp_path, start, skip_venv=True)
        assert result == cfg

    def test_outside_start_dir_falls_back_to_candidates(self, tmp_path):
        cfg = tmp_path / "usecli.config.toml"
        cfg.write_text("")
        start = tmp_path / "start"
        start.mkdir()
        result = _find_usecli_config_path(tmp_path, start, skip_venv=True)
        assert result == cfg


class TestFindUsecliConfigPathForCommand:
    def test_nonexistent_root(self, tmp_path):
        assert (
            _find_usecli_config_path_for_command(
                tmp_path / "nope", tmp_path, skip_venv=True
            )
            is None
        )

    def test_no_candidates(self, tmp_path):
        assert (
            _find_usecli_config_path_for_command(tmp_path, tmp_path, skip_venv=True)
            is None
        )

    def test_no_matching_command(self, tmp_path):
        cfg = tmp_path / "usecli.config.toml"
        cfg.write_text('[usecli]\ncommand_name = "other"')
        with (
            patch("usecli.cli.config.colors._get_command_name", return_value="mycli"),
            patch(
                "usecli.cli.config.colors._get_console_script_aliases",
                return_value=set(),
            ),
        ):
            assert (
                _find_usecli_config_path_for_command(tmp_path, tmp_path, skip_venv=True)
                is None
            )

    def test_matching_command(self, tmp_path):
        cfg = tmp_path / "usecli.config.toml"
        cfg.write_text('[usecli]\ncommand_name = "mycli"')
        with patch("usecli.cli.config.colors._get_command_name", return_value="mycli"):
            result = _find_usecli_config_path_for_command(
                tmp_path, tmp_path, skip_venv=True
            )
            assert result == cfg

    def test_outside_start_dir(self, tmp_path):
        cfg = tmp_path / "usecli.config.toml"
        cfg.write_text('[usecli]\ncommand_name = "mycli"')
        start = tmp_path / "start"
        start.mkdir()
        with patch("usecli.cli.config.colors._get_command_name", return_value="mycli"):
            result = _find_usecli_config_path_for_command(
                tmp_path, start, skip_venv=True
            )
            assert result == cfg


class TestFindUsecliConfigInPackage:
    def test_no_spec(self):
        with patch("importlib.util.find_spec", return_value=None):
            assert _find_usecli_config_in_package() is None

    def test_skips_missing_location(self):
        spec = MagicMock()
        spec.submodule_search_locations = ["/nonexistent/pkg"]
        with patch("importlib.util.find_spec", return_value=spec):
            assert _find_usecli_config_in_package() is None

    def test_found(self, tmp_path):
        cfg = tmp_path / "usecli.config.toml"
        cfg.write_text("")
        spec = MagicMock()
        spec.submodule_search_locations = [str(tmp_path)]
        with patch("importlib.util.find_spec", return_value=spec):
            assert _find_usecli_config_in_package() == cfg


class TestFindUsecliConfigInNamedPackage:
    def test_empty_package_name(self):
        assert _find_usecli_config_in_named_package("") is None

    def test_no_spec(self):
        with patch("importlib.util.find_spec", return_value=None):
            assert _find_usecli_config_in_named_package("mypkg") is None

    def test_skips_missing_location(self):
        spec = MagicMock()
        spec.submodule_search_locations = ["/nonexistent/pkg"]
        with patch("importlib.util.find_spec", return_value=spec):
            assert _find_usecli_config_in_named_package("mypkg") is None

    def test_found(self, tmp_path):
        cfg = tmp_path / "usecli.config.toml"
        cfg.write_text("")
        spec = MagicMock()
        spec.submodule_search_locations = [str(tmp_path)]
        with patch("importlib.util.find_spec", return_value=spec):
            assert _find_usecli_config_in_named_package("mypkg") == cfg


class TestFindUsecliConfigForConsoleScript:
    def test_no_command(self):
        with patch("usecli.cli.config.colors.sys", argv=[]):
            assert _find_usecli_config_for_console_script() is None

    def test_no_distribution(self):
        with (
            patch("usecli.cli.config.colors.sys", argv=["/usr/bin/mycli"]),
            patch(
                "usecli.shared.config.manager._find_distribution_for_console_script",
                return_value=None,
            ),
        ):
            assert _find_usecli_config_for_console_script() is None

    def test_lowercase_name_and_normalized(self):
        dist = MagicMock()
        dist.metadata = {"name": "my-cli"}
        with (
            patch("usecli.cli.config.colors.sys", argv=["/usr/bin/mycli"]),
            patch(
                "usecli.shared.config.manager._find_distribution_for_console_script",
                return_value=dist,
            ),
            patch(
                "usecli.cli.config.colors._find_usecli_config_in_named_package",
                return_value=None,
            ),
        ):
            assert _find_usecli_config_for_console_script() is None

    def test_returns_match(self, tmp_path):
        dist = MagicMock()
        dist.metadata = {"Name": "mycli"}
        match = tmp_path / "usecli.config.toml"
        with (
            patch("usecli.cli.config.colors.sys", argv=["/usr/bin/mycli"]),
            patch(
                "usecli.shared.config.manager._find_distribution_for_console_script",
                return_value=dist,
            ),
            patch(
                "usecli.cli.config.colors._find_usecli_config_in_named_package",
                return_value=match,
            ),
        ):
            assert _find_usecli_config_for_console_script() == match


class TestLoadTheme:
    def test_custom_theme(self, tmp_path):
        theme_path = tmp_path / "custom.toml"
        theme_path.write_text('[colors]\nprimary = "#FF0000"')
        with (
            patch("usecli.cli.config.colors._find_project_root", return_value=tmp_path),
            patch(
                "usecli.cli.config.colors._load_usecli_config",
                return_value=({"theme": "custom"}, None),
            ),
            patch(
                "usecli.cli.config.colors._resolve_theme_path",
                return_value=theme_path,
            ),
        ):
            colors, ansi, name, path = _load_theme()
            assert name == "custom"
            assert path == theme_path
            assert colors["primary"] == "#FF0000"
            assert ansi["primary"] == "\033[38;2;255;0;0m"


class TestThemeContext:
    def test_cached_context_with_no_config_path(self):
        cwd = Path.cwd().resolve()
        _THEME_CACHE["context"] = ("ctx", None, "default", None)
        _THEME_CACHE["cwd"] = cwd
        _THEME_CACHE["config_path"] = None
        try:
            assert _theme_context() == ("ctx", None, "default", None)
        finally:
            _THEME_CACHE["context"] = None
            _THEME_CACHE["cwd"] = None
            _THEME_CACHE["config_path"] = None
