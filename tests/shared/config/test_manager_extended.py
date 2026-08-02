"""Extended tests for usecli.shared.config.manager — utility functions and ConfigManager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from usecli.shared.config.manager import (
    ConfigManager,
    _dedupe_items,
    _deep_merge,
    _find_distribution_for_console_script,
    _get_distributions,
    _get_package_name,
    _normalize_themes_dir,
    _reset_distributions_cache,
    _rglob_limited,
    _walk_for_filename,
    get_config,
    reset_config,
)

# ---------------------------------------------------------------------------
# Pure utility functions
# ---------------------------------------------------------------------------


class TestDeepMerge:
    def test_merges_flat_dicts(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merges_nested_dicts(self):
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 3, "z": 4}}
        result = _deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_does_not_mutate_original(self):
        base = {"a": 1}
        override = {"b": 2}
        _deep_merge(base, override)
        assert base == {"a": 1}

    def test_override_replaces_non_dict_with_dict(self):
        base = {"a": 1}
        override = {"a": {"nested": True}}
        result = _deep_merge(base, override)
        assert result == {"a": {"nested": True}}


class TestNormalizeThemesDir:
    def test_returns_empty_for_none(self):
        assert _normalize_themes_dir(None) == []

    def test_handles_string_value(self):
        assert _normalize_themes_dir("themes") == ["themes"]

    def test_handles_empty_string(self):
        assert _normalize_themes_dir("") == []

    def test_handles_whitespace_string(self):
        assert _normalize_themes_dir("   ") == []

    def test_handles_list_value(self):
        assert _normalize_themes_dir(["dir1", "dir2"]) == ["dir1", "dir2"]

    def test_skips_empty_strings_in_list(self):
        assert _normalize_themes_dir(["", "valid", "  "]) == ["valid"]

    def test_skips_non_strings_in_list(self):
        assert _normalize_themes_dir([42, "valid"]) == ["valid"]

    def test_returns_empty_for_other_types(self):
        assert _normalize_themes_dir(42) == []


class TestDedupeItems:
    def test_removes_duplicates(self):
        assert _dedupe_items(["a", "b", "a", "c"]) == ["a", "b", "c"]

    def test_preserves_order(self):
        assert _dedupe_items(["c", "a", "b"]) == ["c", "a", "b"]

    def test_empty_list(self):
        assert _dedupe_items([]) == []


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


class TestRglobLimited:
    def test_finds_file(self, tmp_path):
        target = tmp_path / "test.txt"
        target.write_text("hello")
        result = _rglob_limited(tmp_path, "test.txt", skip_venv=False, max_depth=6)
        assert target in result

    def test_returns_empty_when_not_found(self, tmp_path):
        result = _rglob_limited(tmp_path, "nonexistent.txt", skip_venv=False)
        assert result == []


# ---------------------------------------------------------------------------
# Distribution helpers
# ---------------------------------------------------------------------------


class TestGetPackageName:
    def test_returns_package_name(self):
        result = _get_package_name()
        assert isinstance(result, str)
        assert len(result) > 0


class TestGetDistributions:
    def test_returns_list(self):
        result = _get_distributions()
        assert isinstance(result, list)

    def test_caches_result(self):
        _reset_distributions_cache()
        result1 = _get_distributions()
        result2 = _get_distributions()
        assert result1 is result2


class TestFindDistributionForConsoleScript:
    def test_returns_none_for_empty_command(self):
        assert _find_distribution_for_console_script("") is None

    def test_returns_none_for_none_command(self):
        assert _find_distribution_for_console_script(None) is None


# ---------------------------------------------------------------------------
# ConfigManager
# ---------------------------------------------------------------------------


class TestConfigManagerInit:
    def test_init_with_defaults(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        assert manager.start_dir == tmp_path
        assert manager.pyproject_path == tmp_path / "pyproject.toml"

    def test_init_with_custom_pyproject(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"')
        manager = ConfigManager(pyproject_path=pyproject, start_dir=tmp_path)
        assert manager.pyproject_path == pyproject


class TestConfigManagerPyprojectHasUsecli:
    def test_returns_false_for_nonexistent_file(self, tmp_path):
        assert (
            ConfigManager._pyproject_has_usecli(tmp_path / "nonexistent.toml") is False
        )

    def test_returns_true_when_usecli_in_tool(self, tmp_path):
        path = tmp_path / "pyproject.toml"
        path.write_text('[tool.usecli]\ntheme = "dark"')
        assert ConfigManager._pyproject_has_usecli(path) is True

    def test_returns_false_when_no_usecli_in_tool(self, tmp_path):
        path = tmp_path / "pyproject.toml"
        path.write_text("[tool.ruff]\nline-length = 88")
        assert ConfigManager._pyproject_has_usecli(path) is False

    def test_returns_false_for_invalid_toml(self, tmp_path):
        path = tmp_path / "pyproject.toml"
        path.write_text("not = = valid")
        assert ConfigManager._pyproject_has_usecli(path) is False


class TestConfigManagerFindPyprojectToml:
    def test_finds_in_current_dir(self, tmp_path):
        path = tmp_path / "pyproject.toml"
        path.write_text("")
        result = ConfigManager._find_pyproject_toml(tmp_path)
        assert result == path

    def test_finds_in_parent_dir(self, tmp_path):
        nested = tmp_path / "src" / "deep"
        nested.mkdir(parents=True)
        path = tmp_path / "pyproject.toml"
        path.write_text("")
        result = ConfigManager._find_pyproject_toml(nested)
        assert result == path

    def test_returns_none_when_not_found(self, tmp_path):
        result = ConfigManager._find_pyproject_toml(tmp_path)
        assert result is None


class TestConfigManagerGetCommandName:
    def test_returns_none_for_empty_argv(self):
        with patch("usecli.shared.config.manager.sys", argv=[]):
            assert ConfigManager._get_command_name() is None

    def test_returns_basename(self):
        with patch("usecli.shared.config.manager.sys", argv=["/usr/bin/mycli"]):
            assert ConfigManager._get_command_name() == "mycli"


class TestConfigManagerPublicAPI:
    def test_get_returns_value(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        result = manager.get("title")
        assert result is not None

    def test_get_returns_default_for_missing_key(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        result = manager.get("nonexistent_key", "default_val")
        assert result == "default_val"

    def test_has_key_returns_true_for_existing(self, tmp_path):
        config_path = tmp_path / "usecli.config.toml"
        config_path.write_text('[usecli]\ntitle = "My App"')
        manager = ConfigManager(usecli_config_path=config_path, start_dir=tmp_path)
        assert manager.has_key("title") is True

    def test_has_key_returns_false_for_missing(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        assert manager.has_key("nonexistent_key") is False

    def test_get_project_root(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        assert manager.get_project_root() is not None

    def test_get_project_version(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        result = manager.get_project_version()
        # May be None if no version in pyproject.toml
        assert result is None or isinstance(result, str)

    def test_is_usecli_direct_dependency(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        result = manager.is_usecli_direct_dependency()
        assert isinstance(result, bool)

    def test_get_project_paths(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        paths = manager.get_project_paths()
        assert "commands_dir" in paths
        assert "templates_dir" in paths
        assert "themes_dir" in paths


class TestGetConfig:
    def test_returns_config_manager(self):
        result = get_config()
        assert isinstance(result, ConfigManager)


class TestResetConfig:
    def test_reset_creates_new_instance(self):
        config1 = get_config()
        reset_config()
        config2 = get_config()
        assert config1 is not config2
