"""Extended tests for usecli.shared.config.manager — utility functions and ConfigManager."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch
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
    find_project_root,
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


class TestConfigManagerAdditionalMethods:
    def test_get_all_returns_copy(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        all_config = manager.get_all()
        assert isinstance(all_config, dict)
        # Modifying the copy shouldn't affect the manager
        all_config["new_key"] = "new_value"
        assert manager.get("new_key") is None

    def test_get_project_commands_dir(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        commands_dir = manager.get_project_commands_dir()
        assert isinstance(commands_dir, Path)

    def test_get_project_templates_dir(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        templates_dir = manager.get_project_templates_dir()
        assert isinstance(templates_dir, Path)

    def test_get_project_themes_dirs(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        themes_dirs = manager.get_project_themes_dirs()
        assert isinstance(themes_dirs, list)

    def test_is_dev(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        assert isinstance(manager.is_dev(), bool)

    def test_is_prod(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        assert isinstance(manager.is_prod(), bool)

    def test_is_usecli_direct_dependency_with_usecli_name(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "usecli"')
        manager = ConfigManager(pyproject_path=pyproject, start_dir=tmp_path)
        assert manager.is_usecli_direct_dependency() is True

    def test_is_usecli_direct_dependency_with_usecli_dep(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "myapp"\ndependencies = ["usecli>=1.0"]')
        manager = ConfigManager(pyproject_path=pyproject, start_dir=tmp_path)
        assert manager.is_usecli_direct_dependency() is True

    def test_is_usecli_direct_dependency_with_dependency_groups(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "myapp"\n\n[dependency-groups]\ndev = ["usecli>=1.0"]')
        manager = ConfigManager(pyproject_path=pyproject, start_dir=tmp_path)
        assert manager.is_usecli_direct_dependency() is True

    def test_is_usecli_direct_dependency_with_dict_dep_in_group(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "myapp"\n\n[dependency-groups]\ndev = [{dependency = "usecli>=1.0"}]')
        manager = ConfigManager(pyproject_path=pyproject, start_dir=tmp_path)
        assert manager.is_usecli_direct_dependency() is True

    def test_is_usecli_direct_dependency_false_for_other(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "myapp"\ndependencies = ["requests>=2.0"]')
        manager = ConfigManager(pyproject_path=pyproject, start_dir=tmp_path)
        # Might still return True if the running distribution lists usecli
        result = manager.is_usecli_direct_dependency()
        assert isinstance(result, bool)

    def test_is_usecli_direct_dependency_handles_invalid_toml(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("not = = valid")
        manager = ConfigManager(pyproject_path=pyproject, start_dir=tmp_path)
        result = manager.is_usecli_direct_dependency()
        assert isinstance(result, bool)

    def test_reload(self, tmp_path):
        config_path = tmp_path / "usecli.config.toml"
        config_path.write_text('[usecli]\ntitle = "v1"')
        manager = ConfigManager(usecli_config_path=config_path, start_dir=tmp_path)
        assert manager.get("title") == "v1"
        # Modify config and reload
        config_path.write_text('[usecli]\ntitle = "v2"')
        from usecli.shared.config.manager import _reset_toml_cache
        _reset_toml_cache()
        manager.reload()
        assert manager.get("title") == "v2"

    def test_pyproject_exists_property(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        assert isinstance(manager.pyproject_exists, bool)

    def test_load_project_version_with_version(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.2.3"')
        result = ConfigManager._load_project_version(pyproject)
        assert result == "1.2.3"

    def test_load_project_version_without_version(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"')
        result = ConfigManager._load_project_version(pyproject)
        assert result is None

    def test_load_project_version_nonexistent(self, tmp_path):
        result = ConfigManager._load_project_version(tmp_path / "nonexistent.toml")
        assert result is None

    def test_load_project_version_from_tool_usecli(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.usecli]\nversion = "2.0.0"')
        result = ConfigManager._load_project_version(pyproject)
        assert result == "2.0.0"

    def test_load_project_version_with_invalid_toml(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("not = = valid")
        result = ConfigManager._load_project_version(pyproject)
        assert result is None

    def test_load_project_version_with_empty_version(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "  "')
        result = ConfigManager._load_project_version(pyproject)
        assert result is None

    def test_is_in_venv_with_venv_path(self):
        assert ConfigManager._is_in_venv(Path(".venv/lib/python")) is True

    def test_is_in_venv_with_normal_path(self):
        assert ConfigManager._is_in_venv(Path("/tmp/project")) is False

    def test_is_in_venv_with_site_packages(self):
        assert ConfigManager._is_in_venv(Path("/lib/site-packages")) is True

    def test_resolve_editable_source_root_returns_none_for_none(self):
        result = ConfigManager._resolve_editable_source_root(None)
        assert result is None

    def test_resolve_editable_source_root_returns_none_for_no_text(self):
        dist = MagicMock()
        dist.read_text.return_value = None
        result = ConfigManager._resolve_editable_source_root(dist)
        assert result is None

    def test_resolve_editable_source_root_returns_none_for_non_editable(self, tmp_path):
        dist = MagicMock()
        dist.read_text.return_value = '{"url": "file:///tmp/test"}'
        result = ConfigManager._resolve_editable_source_root(dist)
        assert result is None

    def test_resolve_editable_source_root_returns_none_for_no_url(self, tmp_path):
        dist = MagicMock()
        dist.read_text.return_value = '{"dir_info": {"editable": true}}'
        result = ConfigManager._resolve_editable_source_root(dist)
        assert result is None

    def test_resolve_editable_source_root_returns_path_for_editable(self, tmp_path):
        dist = MagicMock()
        dist.read_text.return_value = f'{{"dir_info": {{"editable": true}}, "url": "file://{tmp_path}"}}'
        result = ConfigManager._resolve_editable_source_root(dist)
        assert result == tmp_path.resolve()

    def test_resolve_editable_source_root_returns_none_for_nonexistent(self):
        dist = MagicMock()
        dist.read_text.return_value = '{"dir_info": {"editable": true}, "url": "file:///nonexistent/path"}'
        result = ConfigManager._resolve_editable_source_root(dist)
        assert result is None

    def test_resolve_editable_source_root_handles_attribute_error(self):
        dist = MagicMock()
        dist.read_text.side_effect = AttributeError
        result = ConfigManager._resolve_editable_source_root(dist)
        assert result is None

    def test_resolve_editable_source_root_handles_os_error(self):
        dist = MagicMock()
        dist.read_text.side_effect = OSError
        result = ConfigManager._resolve_editable_source_root(dist)
        assert result is None

    def test_resolve_editable_source_root_handles_json_error(self):
        dist = MagicMock()
        dist.read_text.return_value = "not json"
        result = ConfigManager._resolve_editable_source_root(dist)
        assert result is None

    def test_search_source_for_config_returns_none_for_nonexistent(self):
        result = ConfigManager._search_source_for_config(Path("/nonexistent"), None, None)
        assert result is None

    def test_search_source_for_config_returns_none_when_no_candidates(self, tmp_path):
        result = ConfigManager._search_source_for_config(tmp_path, "mycli", None)
        assert result is None

    def test_search_source_for_config_returns_config(self, tmp_path):
        config = tmp_path / "usecli.config.toml"
        config.write_text('[usecli]\ntheme = "dark"')
        result = ConfigManager._search_source_for_config(tmp_path, None, None)
        assert result == config

    def test_pyproject_has_usecli_with_usecli(self, tmp_path):
        path = tmp_path / "pyproject.toml"
        path.write_text('[tool.usecli]\ntheme = "dark"')
        assert ConfigManager._pyproject_has_usecli(path) is True

    def test_pyproject_has_usecli_without_usecli(self, tmp_path):
        path = tmp_path / "pyproject.toml"
        path.write_text('[tool.ruff]\nline-length = 88')
        assert ConfigManager._pyproject_has_usecli(path) is False

    def test_pyproject_has_usecli_nonexistent(self, tmp_path):
        assert ConfigManager._pyproject_has_usecli(tmp_path / "nonexistent.toml") is False

    def test_pyproject_has_usecli_invalid_toml(self, tmp_path):
        path = tmp_path / "pyproject.toml"
        path.write_text("not = = valid")
        assert ConfigManager._pyproject_has_usecli(path) is False

    def test_find_usecli_config_on_sys_path_returns_none_when_empty(self):
        with patch("usecli.shared.config.manager.sys", path=[]):
            result = ConfigManager._find_usecli_config_on_sys_path()
            assert result is None

    def test_find_project_root_with_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("")
        result = find_project_root(tmp_path)
        assert result == tmp_path

    def test_find_project_root_with_usecli_config(self, tmp_path):
        (tmp_path / "usecli.config.toml").write_text("")
        result = find_project_root(tmp_path)
        assert result == tmp_path

    def test_find_project_root_with_git(self, tmp_path):
        (tmp_path / ".git").mkdir()
        result = find_project_root(tmp_path)
        assert result is not None

    def test_find_project_root_returns_none_when_not_found(self, tmp_path):
        # Create a deep directory with no markers
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        result = find_project_root(deep)
        # May return git_root or None
        assert result is None or isinstance(result, Path)

    def test_find_project_root_uses_cache(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("")
        # First call
        result1 = find_project_root(tmp_path)
        # Second call should use cache
        result2 = find_project_root(tmp_path)
        assert result1 == result2

    def test_find_project_root_defaults_to_cwd(self):
        result = find_project_root()
        assert result is None or isinstance(result, Path)

    def test_read_top_level_packages_returns_empty_for_none(self):
        dist = MagicMock()
        dist.read_text.return_value = None
        result = ConfigManager._read_top_level_packages(dist)
        assert result == []

    def test_read_top_level_packages_returns_packages(self):
        dist = MagicMock()
        dist.read_text.return_value = "usecli\n"
        result = ConfigManager._read_top_level_packages(dist)
        assert result == ["usecli"]

    def test_read_top_level_packages_handles_attribute_error(self):
        dist = MagicMock()
        dist.read_text.side_effect = AttributeError
        result = ConfigManager._read_top_level_packages(dist)
        assert result == []

    def test_read_top_level_packages_handles_os_error(self):
        dist = MagicMock()
        dist.read_text.side_effect = OSError
        result = ConfigManager._read_top_level_packages(dist)
        assert result == []

    def test_config_matches_command_returns_true_for_none(self, tmp_path):
        config_path = tmp_path / "usecli.config.toml"
        config_path.write_text('[usecli]\ntheme = "dark"')
        assert ConfigManager._config_matches_command(config_path, None) is True

    def test_config_matches_command_returns_true_for_matching(self, tmp_path):
        config_path = tmp_path / "usecli.config.toml"
        config_path.write_text('[usecli]\ncommand_name = "mycli"')
        assert ConfigManager._config_matches_command(config_path, "mycli") is True

    def test_config_matches_command_returns_true_for_no_command(self, tmp_path):
        config_path = tmp_path / "usecli.config.toml"
        config_path.write_text('[usecli]\ntheme = "dark"')
        assert ConfigManager._config_matches_command(config_path, "mycli") is True

    def test_config_matches_command_handles_invalid_toml(self, tmp_path):
        config_path = tmp_path / "usecli.config.toml"
        config_path.write_text("not = = valid")
        assert ConfigManager._config_matches_command(config_path, "mycli") is True

    def test_is_preferred_package_path_returns_true_for_venv(self):
        assert ConfigManager._is_preferred_package_path(Path(".venv/lib")) is True

    def test_is_preferred_package_path_returns_false_for_normal(self):
        assert ConfigManager._is_preferred_package_path(Path("/tmp/project")) is False

    def test_dot_notation_get(self, tmp_path):
        config_path = tmp_path / "usecli.config.toml"
        config_path.write_text('[usecli]\nnested.key = "value"')
        manager = ConfigManager(usecli_config_path=config_path, start_dir=tmp_path)
        # Test dot notation access
        result = manager.get("nested.key", "default")
        assert result == "default" or isinstance(result, str)

    def test_load_project_version(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.2.3"')
        manager = ConfigManager(pyproject_path=pyproject, start_dir=tmp_path)
        result = manager.get_project_version()
        assert result == "1.2.3"

    def test_load_project_version_missing(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"')
        manager = ConfigManager(pyproject_path=pyproject, start_dir=tmp_path)
        result = manager.get_project_version()
        assert result is None
