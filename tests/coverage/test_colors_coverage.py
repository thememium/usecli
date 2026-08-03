"""Coverage-focused tests for usecli.cli.config.colors.

Targets uncovered branches in colors.py (config discovery, theme loading,
console-script resolution, and error paths) without modifying source.
"""

from __future__ import annotations

import types
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

from usecli.cli.config.colors import (
    _THEME_CACHE,
    _config_matches_command,
    _find_project_root,
    _find_usecli_config_for_console_script,
    _find_usecli_config_in_named_package,
    _find_usecli_config_in_package,
    _find_usecli_config_path,
    _find_usecli_config_path_for_command,
    _get_console_script_aliases,
    _get_package_name,
    _import_tomllib,
    _is_within_usecli_package,
    _load_theme,
    _load_theme_file,
    _load_usecli_config,
    _load_usecli_config_file,
    _resolve_theme_path,
    _theme_context,
    _walk_for_filename,
)


class TestImportTomllib:
    def test_imports_tomli_on_py_lt_311(self):
        fake = types.ModuleType("tomli")
        with (
            patch("usecli.cli.config.colors.sys.version_info", (3, 10)),
            patch.dict("sys.modules", {"tomli": fake}),
        ):
            assert _import_tomllib() is fake


class TestWalkForFilename:
    def test_continues_on_oserror_for_entry(self):
        entry = MagicMock()
        entry.is_file.side_effect = OSError("boom")
        entry.is_dir.side_effect = OSError("boom")
        fake_dir = MagicMock()
        fake_dir.iterdir.return_value = [entry]
        results: list[Path] = []
        _walk_for_filename(fake_dir, "test.txt", 0, 6, frozenset(), results)
        assert results == []


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


class TestConfigMatchesCommand:
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


class TestGetConsoleScriptAliases:
    def test_handles_oserror_on_entry_points(self):
        mock_dist = MagicMock()
        type(mock_dist).entry_points = PropertyMock(side_effect=OSError("boom"))
        with patch(
            "usecli.shared.config.manager._find_distribution_for_console_script",
            return_value=mock_dist,
        ):
            result = _get_console_script_aliases("mycli")
            assert "mycli" in result


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


class TestIsWithinUsecliPackage:
    def test_no_spec(self):
        with patch("importlib.util.find_spec", return_value=None):
            assert _is_within_usecli_package(Path("/tmp/x")) is False

    def test_within_package(self, tmp_path):
        spec = MagicMock()
        spec.submodule_search_locations = [str(tmp_path)]
        with patch("importlib.util.find_spec", return_value=spec):
            assert _is_within_usecli_package(tmp_path / "sub") is True


class TestFindProjectRoot:
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


class TestLoadUsecliConfig:
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


class TestLoadUsecliConfigFile:
    def test_usecli_not_a_dict(self, tmp_path):
        cfg = tmp_path / "config.toml"
        cfg.write_text('usecli = "not a dict"')
        assert _load_usecli_config_file(cfg) == {}


class TestGetPackageName:
    def test_empty_package_returns_usecli(self):
        with (
            patch("usecli.cli.config.colors.__package__", ""),
            patch("usecli.cli.config.colors.__name__", ""),
        ):
            assert _get_package_name() == "usecli"


class TestResolveThemePath:
    def test_not_found_in_theme_dirs(self, tmp_path):
        assert _resolve_theme_path("nonexistent", tmp_path, {}) is None


class TestLoadThemeFile:
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
