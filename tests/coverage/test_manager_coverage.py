"""Coverage-focused tests for usecli.shared.config.manager.

Targets uncovered branches in manager.py (config discovery, TOML loading,
validation, dependency checks, path discovery, and error/fallback paths)
without modifying source.
"""

from __future__ import annotations

import sys
import types
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest

from usecli.shared.config.manager import (
    ConfigManager,
    _config_search_cache,
    _find_distribution_for_console_script,
    _get_distributions,
    _get_package_name,
    _get_tomllib,
    _reset_distributions_cache,
    _reset_project_root_cache,
    _reset_toml_cache,
    _walk_for_filename,
    find_project_root,
    reset_config,
)


@pytest.fixture(autouse=True)
def _clean_caches():
    """Reset all module-level caches to avoid order dependence."""
    reset_config()
    _reset_toml_cache()
    _reset_distributions_cache()
    _reset_project_root_cache()
    _config_search_cache.clear()
    yield
    reset_config()
    _reset_toml_cache()
    _reset_distributions_cache()
    _reset_project_root_cache()
    _config_search_cache.clear()


# ---------------------------------------------------------------------------
# _get_tomllib
# ---------------------------------------------------------------------------


class TestGetTomllib:
    def test_imports_tomli_on_py_lt_311(self):
        fake = types.ModuleType("tomli")
        with (
            patch("usecli.shared.config.manager.sys.version_info", (3, 10)),
            patch.dict(sys.modules, {"tomli": fake}),
        ):
            assert _get_tomllib() is fake


# ---------------------------------------------------------------------------
# _walk_for_filename
# ---------------------------------------------------------------------------


class TestWalkForFilenameErrors:
    def test_continues_when_entry_raises_oserror(self):
        class FakeEntry:
            def is_file(self):
                raise OSError("boom")

            def is_dir(self):
                raise OSError("boom")

        class FakeDir:
            def iterdir(self):
                return [FakeEntry()]

        results: list[Path] = []
        _walk_for_filename(FakeDir(), "test.txt", 0, 6, frozenset(), results)  # type: ignore[ty:invalid-argument-type]
        assert results == []


# ---------------------------------------------------------------------------
# _get_distributions
# ---------------------------------------------------------------------------


class TestGetDistributionsErrors:
    def test_returns_empty_on_oserror(self):
        _reset_distributions_cache()

        class FakeMeta:
            def distributions(self):
                raise OSError("boom")

        with patch(
            "usecli.shared.config.manager._get_importlib_metadata",
            return_value=FakeMeta(),
        ):
            assert _get_distributions() == []


# ---------------------------------------------------------------------------
# _find_distribution_for_console_script
# ---------------------------------------------------------------------------


class TestFindDistributionForConsoleScript:
    def test_fast_path2_exception(self):
        class FakeMeta:
            def distribution(self, name):
                raise PackageNotFoundError

        with (
            patch(
                "usecli.shared.config.manager._get_importlib_metadata",
                return_value=FakeMeta(),
            ),
            patch(
                "usecli.shared.config.manager._get_package_name",
                return_value="otherpkg",
            ),
            patch(
                "usecli.shared.config.manager._get_distributions",
                return_value=[],
            ),
        ):
            assert _find_distribution_for_console_script("mycmd") is None

    def test_fast_path2_success(self):
        class FakeEP:
            group = "console_scripts"
            name = "mycmd"

        class FakeDistNoMatch:
            entry_points: ClassVar[list] = []

        class FakeDistMatch:
            entry_points: ClassVar[list] = [FakeEP()]

        match_dist = FakeDistMatch()

        class FakeMeta:
            def distribution(self, name):
                if name == "mycmd":
                    return FakeDistNoMatch()
                return match_dist

        with (
            patch(
                "usecli.shared.config.manager._get_importlib_metadata",
                return_value=FakeMeta(),
            ),
            patch(
                "usecli.shared.config.manager._get_package_name",
                return_value="otherpkg",
            ),
        ):
            assert _find_distribution_for_console_script("mycmd") is match_dist

    def test_slow_path_exception(self):
        class FakeDist:
            @property
            def entry_points(self):
                raise AttributeError

        class FakeMeta:
            def distribution(self, name):
                raise PackageNotFoundError

        with (
            patch(
                "usecli.shared.config.manager._get_importlib_metadata",
                return_value=FakeMeta(),
            ),
            patch(
                "usecli.shared.config.manager._get_package_name",
                return_value="mycmd",
            ),
            patch(
                "usecli.shared.config.manager._get_distributions",
                return_value=[FakeDist()],
            ),
        ):
            assert _find_distribution_for_console_script("mycmd") is None


# ---------------------------------------------------------------------------
# ConfigManager.__init__ project_root resolution
# ---------------------------------------------------------------------------


class TestConfigManagerInitRoot:
    def test_detected_root_none_uses_config_parent(self, tmp_path):
        config = tmp_path / "usecli.config.toml"
        config.write_text('[usecli]\ntitle = "x"')
        with patch("usecli.shared.config.manager.find_project_root", return_value=None):
            manager = ConfigManager(usecli_config_path=config, start_dir=tmp_path)
        assert manager.project_root == tmp_path.resolve()

    def test_relative_to_value_error_uses_config_parent(self, tmp_path):
        real = tmp_path / "real"
        real.mkdir()
        config = real / "usecli.config.toml"
        config.write_text('[usecli]\ntitle = "x"')
        link = tmp_path / "link"
        link.symlink_to(real, target_is_directory=True)
        with patch("usecli.shared.config.manager.find_project_root", return_value=link):
            manager = ConfigManager(usecli_config_path=config, start_dir=tmp_path)
        assert manager.project_root == real.resolve()

    def test_framework_in_venv_uses_start_dir(self, tmp_path):
        venv_root = tmp_path / ".venv" / "lib" / "site-packages"
        with (
            patch(
                "usecli.shared.config.manager.find_project_root",
                return_value=venv_root,
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._get_command_name",
                return_value="usecli",
            ),
        ):
            manager = ConfigManager(
                usecli_config_path=tmp_path / "usecli.config.toml",
                start_dir=tmp_path,
            )
        assert manager.project_root == tmp_path.resolve()


# ---------------------------------------------------------------------------
# _find_usecli_config discovery branches
# ---------------------------------------------------------------------------


class TestFindUsecliConfig:
    def test_package_match(self, tmp_path):
        target = tmp_path / "pkg" / "usecli.config.toml"
        target.parent.mkdir(parents=True)
        target.write_text('[usecli]\ntitle = "x"')
        with (
            patch(
                "usecli.shared.config.manager.ConfigManager._find_usecli_config_for_console_script",
                return_value=None,
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._is_within_usecli_package",
                return_value=True,
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._find_usecli_config_in_package",
                return_value=target,
            ),
        ):
            result = ConfigManager._find_usecli_config(tmp_path)
        assert result == target

    def test_sys_path_match(self, tmp_path):
        target = tmp_path / "sys" / "usecli.config.toml"
        target.parent.mkdir(parents=True)
        target.write_text('[usecli]\ntitle = "x"')
        with (
            patch(
                "usecli.shared.config.manager.ConfigManager._find_usecli_config_for_console_script",
                return_value=None,
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._is_within_usecli_package",
                return_value=True,
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._find_usecli_config_in_package",
                return_value=None,
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._find_usecli_config_on_sys_path",
                return_value=target,
            ),
        ):
            result = ConfigManager._find_usecli_config(tmp_path)
        assert result == target

    def test_high_level_search_root_returns_none(self, tmp_path):
        with (
            patch(
                "usecli.shared.config.manager.ConfigManager._find_usecli_config_for_console_script",
                return_value=None,
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._is_within_usecli_package",
                return_value=False,
            ),
            patch(
                "usecli.shared.config.manager.find_project_root",
                return_value=Path("/"),
            ),
        ):
            result = ConfigManager._find_usecli_config(tmp_path)
        assert result is None


# ---------------------------------------------------------------------------
# _find_usecli_config_in_tree
# ---------------------------------------------------------------------------


class TestFindUsecliConfigInTree:
    def test_nonexistent_root_returns_none(self, tmp_path):
        assert (
            ConfigManager._find_usecli_config_in_tree(
                Path("/nonexistent"), tmp_path, skip_venv=True
            )
            is None
        )


# ---------------------------------------------------------------------------
# _find_usecli_config_in_package
# ---------------------------------------------------------------------------


class TestFindUsecliConfigInPackage:
    def test_spec_none_returns_none(self):
        with (
            patch("usecli.shared.config.manager._get_package_name", return_value="pkg"),
            patch(
                "usecli.shared.config.manager.importlib.util.find_spec",
                return_value=None,
            ),
        ):
            assert ConfigManager._find_usecli_config_in_package() is None

    def test_editable_source_root_match(self, tmp_path):
        target = tmp_path / "src" / "usecli.config.toml"
        target.parent.mkdir(parents=True)
        target.write_text('[usecli]\ntitle = "x"')
        spec = types.SimpleNamespace(submodule_search_locations=[str(tmp_path / "pkg")])

        class FakeDist:
            pass

        with (
            patch("usecli.shared.config.manager._get_package_name", return_value="pkg"),
            patch(
                "usecli.shared.config.manager.importlib.util.find_spec",
                return_value=spec,
            ),
            patch("usecli.shared.config.manager._get_importlib_metadata") as gim,
            patch(
                "usecli.shared.config.manager.ConfigManager._resolve_editable_source_root",
                return_value=tmp_path / "src",
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._search_source_for_config",
                return_value=target,
            ),
        ):
            gim.return_value.distribution.return_value = FakeDist()
            assert ConfigManager._find_usecli_config_in_package() == target

    def test_distribution_error_then_loop_match(self, tmp_path):
        pkg_root = tmp_path / "pkg"
        pkg_root.mkdir()
        config = pkg_root / "usecli.config.toml"
        config.write_text('[usecli]\ntitle = "x"')
        spec = types.SimpleNamespace(submodule_search_locations=[str(pkg_root)])

        class FakeMeta:
            def distribution(self, name):
                raise PackageNotFoundError

        with (
            patch("usecli.shared.config.manager._get_package_name", return_value="pkg"),
            patch(
                "usecli.shared.config.manager.importlib.util.find_spec",
                return_value=spec,
            ),
            patch(
                "usecli.shared.config.manager._get_importlib_metadata",
                return_value=FakeMeta(),
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._get_command_name",
                return_value=None,
            ),
        ):
            assert ConfigManager._find_usecli_config_in_package() == config

    def test_nonexistent_location_returns_none(self, tmp_path):
        spec = types.SimpleNamespace(
            submodule_search_locations=[str(tmp_path / "nonexistent")]
        )

        class FakeMeta:
            def distribution(self, name):
                raise PackageNotFoundError

        with (
            patch("usecli.shared.config.manager._get_package_name", return_value="pkg"),
            patch(
                "usecli.shared.config.manager.importlib.util.find_spec",
                return_value=spec,
            ),
            patch(
                "usecli.shared.config.manager._get_importlib_metadata",
                return_value=FakeMeta(),
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._get_command_name",
                return_value=None,
            ),
        ):
            assert ConfigManager._find_usecli_config_in_package() is None

    def test_loop_filters_by_command_name(self, tmp_path):
        pkg_root = tmp_path / "pkg"
        pkg_root.mkdir()
        config = pkg_root / "usecli.config.toml"
        config.write_text('[usecli]\ncommand_name = "mycli"')
        spec = types.SimpleNamespace(submodule_search_locations=[str(pkg_root)])

        class FakeMeta:
            def distribution(self, name):
                raise PackageNotFoundError

        with (
            patch("usecli.shared.config.manager._get_package_name", return_value="pkg"),
            patch(
                "usecli.shared.config.manager.importlib.util.find_spec",
                return_value=spec,
            ),
            patch(
                "usecli.shared.config.manager._get_importlib_metadata",
                return_value=FakeMeta(),
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._get_command_name",
                return_value="mycli",
            ),
        ):
            assert ConfigManager._find_usecli_config_in_package() == config


# ---------------------------------------------------------------------------
# _find_usecli_config_in_named_package
# ---------------------------------------------------------------------------


class TestFindUsecliConfigInNamedPackage:
    def test_empty_package_name_returns_none(self):
        assert ConfigManager._find_usecli_config_in_named_package("") is None

    def test_editable_source_root_match(self, tmp_path):
        target = tmp_path / "src" / "usecli.config.toml"
        target.parent.mkdir(parents=True)
        target.write_text('[usecli]\ntitle = "x"')
        spec = types.SimpleNamespace(submodule_search_locations=[str(tmp_path / "pkg")])

        class FakeDist:
            pass

        with (
            patch(
                "usecli.shared.config.manager.importlib.util.find_spec",
                return_value=spec,
            ),
            patch("usecli.shared.config.manager._get_importlib_metadata") as gim,
            patch(
                "usecli.shared.config.manager.ConfigManager._resolve_editable_source_root",
                return_value=tmp_path / "src",
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._search_source_for_config",
                return_value=target,
            ),
        ):
            gim.return_value.distribution.return_value = FakeDist()
            assert ConfigManager._find_usecli_config_in_named_package("pkg") == target

    def test_nonexistent_location_returns_none(self, tmp_path):
        spec = types.SimpleNamespace(
            submodule_search_locations=[str(tmp_path / "nonexistent")]
        )

        class FakeMeta:
            def distribution(self, name):
                raise PackageNotFoundError

        with (
            patch(
                "usecli.shared.config.manager.importlib.util.find_spec",
                return_value=spec,
            ),
            patch(
                "usecli.shared.config.manager._get_importlib_metadata",
                return_value=FakeMeta(),
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._get_command_name",
                return_value=None,
            ),
        ):
            assert ConfigManager._find_usecli_config_in_named_package("pkg") is None


# ---------------------------------------------------------------------------
# _find_usecli_config_for_console_script
# ---------------------------------------------------------------------------


class TestFindUsecliConfigForConsoleScript:
    def test_empty_argv_returns_none(self):
        with patch("usecli.shared.config.manager.sys", argv=[]):
            assert ConfigManager._find_usecli_config_for_console_script() is None

    def test_no_distribution_returns_none(self):
        with (
            patch("usecli.shared.config.manager.sys", argv=["mycmd"]),
            patch(
                "usecli.shared.config.manager._find_distribution_for_console_script",
                return_value=None,
            ),
        ):
            assert ConfigManager._find_usecli_config_for_console_script() is None

    def test_lowercase_name_metadata(self, tmp_path):
        class FakeDist:
            metadata: ClassVar[dict] = {"name": "mycli"}

            def read_text(self, filename):
                return None

        with (
            patch("usecli.shared.config.manager.sys", argv=["mycmd"]),
            patch(
                "usecli.shared.config.manager._find_distribution_for_console_script",
                return_value=FakeDist(),
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._read_top_level_packages",
                return_value=[],
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._get_console_script_aliases",
                return_value=set(),
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._resolve_editable_source_root",
                return_value=None,
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._find_usecli_config_in_named_package",
                return_value=None,
            ),
        ):
            assert ConfigManager._find_usecli_config_for_console_script() is None

    def test_source_root_match(self, tmp_path):
        target = tmp_path / "src" / "usecli.config.toml"
        target.parent.mkdir(parents=True)
        target.write_text('[usecli]\ntitle = "x"')

        class FakeDist:
            metadata: ClassVar[dict] = {"Name": "mycli"}

            def read_text(self, filename):
                return None

        with (
            patch("usecli.shared.config.manager.sys", argv=["mycmd"]),
            patch(
                "usecli.shared.config.manager._find_distribution_for_console_script",
                return_value=FakeDist(),
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._read_top_level_packages",
                return_value=[],
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._get_console_script_aliases",
                return_value=set(),
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._resolve_editable_source_root",
                return_value=tmp_path / "src",
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._search_source_for_config",
                return_value=target,
            ),
        ):
            assert ConfigManager._find_usecli_config_for_console_script() == target


# ---------------------------------------------------------------------------
# _is_within_usecli_package
# ---------------------------------------------------------------------------


class TestIsWithinUsecliPackage:
    def test_spec_none_returns_false(self):
        with (
            patch("usecli.shared.config.manager._get_package_name", return_value="pkg"),
            patch(
                "usecli.shared.config.manager.importlib.util.find_spec",
                return_value=None,
            ),
        ):
            assert ConfigManager._is_within_usecli_package(Path("/tmp")) is False

    def test_within_package_returns_true(self, tmp_path):
        pkg_root = tmp_path / "pkg"
        pkg_root.mkdir()
        sub = pkg_root / "sub"
        sub.mkdir()
        spec = types.SimpleNamespace(submodule_search_locations=[str(pkg_root)])
        with (
            patch("usecli.shared.config.manager._get_package_name", return_value="pkg"),
            patch(
                "usecli.shared.config.manager.importlib.util.find_spec",
                return_value=spec,
            ),
        ):
            assert ConfigManager._is_within_usecli_package(sub) is True


# ---------------------------------------------------------------------------
# _find_usecli_config_on_sys_path
# ---------------------------------------------------------------------------


class TestFindUsecliConfigOnSysPath:
    def test_no_match_returns_none(self, tmp_path):
        with patch(
            "usecli.shared.config.manager.sys",
            path=["", str(tmp_path / "nonexistent"), str(tmp_path)],
        ):
            assert ConfigManager._find_usecli_config_on_sys_path() is None

    def test_direct_config(self, tmp_path):
        d = tmp_path / "d"
        d.mkdir()
        (d / "usecli.config.toml").write_text('[usecli]\ntitle = "x"')
        with patch("usecli.shared.config.manager.sys", path=[str(d)]):
            assert (
                ConfigManager._find_usecli_config_on_sys_path()
                == d / "usecli.config.toml"
            )

    def test_config_in_subdir(self, tmp_path):
        d = tmp_path / "d"
        sub = d / "sub"
        sub.mkdir(parents=True)
        (sub / "usecli.config.toml").write_text('[usecli]\ntitle = "x"')
        with patch("usecli.shared.config.manager.sys", path=[str(d)]):
            assert (
                ConfigManager._find_usecli_config_on_sys_path()
                == sub / "usecli.config.toml"
            )


# ---------------------------------------------------------------------------
# _load_usecli_toml
# ---------------------------------------------------------------------------


class TestLoadUsecliToml:
    def test_tool_usecli_section(self, tmp_path):
        p = tmp_path / "c.toml"
        p.write_text('[tool.usecli]\ntitle = "x"')
        assert ConfigManager._load_usecli_toml(p) == {"title": "x"}

    def test_no_usecli_section_returns_empty(self, tmp_path):
        p = tmp_path / "c.toml"
        p.write_text('usecli = "notadict"')
        assert ConfigManager._load_usecli_toml(p) == {}


# ---------------------------------------------------------------------------
# _get_console_script_aliases
# ---------------------------------------------------------------------------


class TestGetConsoleScriptAliases:
    def test_none_command_returns_empty(self):
        assert ConfigManager._get_console_script_aliases(None) == set()

    def test_entry_points_error(self):
        class FakeDist:
            @property
            def entry_points(self):
                raise AttributeError

        with patch(
            "usecli.shared.config.manager._find_distribution_for_console_script",
            return_value=FakeDist(),
        ):
            assert ConfigManager._get_console_script_aliases("mycmd") == {"mycmd"}


# ---------------------------------------------------------------------------
# _config_matches_command
# ---------------------------------------------------------------------------


class TestConfigMatchesCommand:
    def test_blank_command_name_returns_true(self, tmp_path):
        p = tmp_path / "c.toml"
        p.write_text('[usecli]\ncommand_name = "   "')
        assert ConfigManager._config_matches_command(p, "mycli") is True


# ---------------------------------------------------------------------------
# _resolve_editable_source_root
# ---------------------------------------------------------------------------


class TestResolveEditableSourceRoot:
    def test_non_dict_json_returns_none(self):
        dist = MagicMock()
        dist.read_text.return_value = "[1, 2]"
        assert ConfigManager._resolve_editable_source_root(dist) is None


# ---------------------------------------------------------------------------
# get_project_commands_dir / get_project_templates_dir (absolute)
# ---------------------------------------------------------------------------


class TestProjectDirsAbsolute:
    def test_commands_dir_absolute(self, tmp_path):
        config = tmp_path / "usecli.config.toml"
        config.write_text('[usecli]\ncommands_dir = "/abs/cmds"')
        manager = ConfigManager(usecli_config_path=config, start_dir=tmp_path)
        assert manager.get_project_commands_dir() == Path("/abs/cmds")

    def test_templates_dir_absolute(self, tmp_path):
        config = tmp_path / "usecli.config.toml"
        config.write_text('[usecli]\ntemplates_dir = "/abs/tmpl"')
        manager = ConfigManager(usecli_config_path=config, start_dir=tmp_path)
        assert manager.get_project_templates_dir() == Path("/abs/tmpl")


# ---------------------------------------------------------------------------
# get_project_paths with a discovered project config
# ---------------------------------------------------------------------------


class TestGetProjectPathsWithConfig:
    def test_with_themes(self, tmp_path):
        config = tmp_path / "usecli.config.toml"
        config.write_text(
            '[usecli]\ncommands_dir = "cmds"\ntemplates_dir = "tmpl"\nthemes_dir = ["th"]'
        )
        manager = ConfigManager(usecli_config_path=config, start_dir=tmp_path)
        with patch.object(manager, "_find_project_config", return_value=config):
            paths = manager.get_project_paths()
        assert paths["commands_dir"] == (tmp_path / "cmds").resolve()
        assert paths["templates_dir"] == (tmp_path / "tmpl").resolve()
        assert paths["themes_dir"] == (tmp_path / "th").resolve()

    def test_default_themes_when_missing(self, tmp_path):
        config = tmp_path / "usecli.config.toml"
        config.write_text('[usecli]\ncommands_dir = "cmds"\ntemplates_dir = "tmpl"')
        manager = ConfigManager(usecli_config_path=config, start_dir=tmp_path)
        with patch.object(manager, "_find_project_config", return_value=config):
            paths = manager.get_project_paths()
        assert paths["themes_dir"] == (tmp_path / "cli" / "themes").resolve()


# ---------------------------------------------------------------------------
# _find_project_config
# ---------------------------------------------------------------------------


class TestFindProjectConfig:
    def test_no_candidates_returns_none(self, tmp_path):
        manager = ConfigManager(start_dir=tmp_path)
        with (
            patch(
                "usecli.shared.config.manager.find_project_root", return_value=tmp_path
            ),
            patch("usecli.shared.config.manager._rglob_limited", return_value=[]),
        ):
            assert manager._find_project_config() is None

    def test_finds_config(self, tmp_path):
        config = tmp_path / "usecli.config.toml"
        config.write_text('[usecli]\ntitle = "x"')
        manager = ConfigManager(start_dir=tmp_path)
        with patch(
            "usecli.shared.config.manager.find_project_root", return_value=tmp_path
        ):
            assert manager._find_project_config() == config


# ---------------------------------------------------------------------------
# is_usecli_direct_dependency
# ---------------------------------------------------------------------------


class TestIsUsecliDirectDependency:
    def test_non_list_dependency_group_skipped(self, tmp_path):
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "myapp"\n\n[dependency-groups]\ndev = "notalist"'
        )
        manager = ConfigManager(pyproject_path=pyproject, start_dir=tmp_path)
        with patch(
            "usecli.shared.config.manager._find_distribution_for_console_script",
            return_value=None,
        ):
            assert manager.is_usecli_direct_dependency() is False

    def test_distribution_name_is_usecli(self, tmp_path):
        class FakeDist:
            metadata: ClassVar[dict] = {"Name": "usecli"}
            requires: ClassVar[list] = []

        manager = ConfigManager(start_dir=tmp_path)
        with (
            patch("usecli.shared.config.manager.sys", argv=["usecli"]),
            patch(
                "usecli.shared.config.manager._find_distribution_for_console_script",
                return_value=FakeDist(),
            ),
        ):
            assert manager.is_usecli_direct_dependency() is True

    def test_distribution_requires_usecli(self, tmp_path):
        class FakeDist:
            metadata: ClassVar[dict] = {"Name": "mycli"}
            requires: ClassVar[list] = ["usecli>=1.0"]

        manager = ConfigManager(start_dir=tmp_path)
        with (
            patch("usecli.shared.config.manager.sys", argv=["mycli"]),
            patch(
                "usecli.shared.config.manager._find_distribution_for_console_script",
                return_value=FakeDist(),
            ),
        ):
            assert manager.is_usecli_direct_dependency() is True


# ---------------------------------------------------------------------------
# _reset_project_root_cache
# ---------------------------------------------------------------------------


class TestResetProjectRootCache:
    def test_clears_cache(self):
        _reset_project_root_cache()


# ---------------------------------------------------------------------------
# find_project_root
# ---------------------------------------------------------------------------


class TestFindProjectRootBranches:
    def test_package_match(self, tmp_path):
        target = tmp_path / "pkg" / "usecli.config.toml"
        target.parent.mkdir(parents=True)
        target.write_text('[usecli]\ntitle = "x"')
        with (
            patch(
                "usecli.shared.config.manager.ConfigManager._find_usecli_config_for_console_script",
                return_value=None,
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._is_within_usecli_package",
                return_value=True,
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._find_usecli_config_in_package",
                return_value=target,
            ),
        ):
            result = find_project_root(tmp_path)
        assert result == target.parent

    def test_high_level_search_root(self, tmp_path):
        with (
            patch(
                "usecli.shared.config.manager.ConfigManager._find_usecli_config_for_console_script",
                return_value=None,
            ),
            patch(
                "usecli.shared.config.manager.ConfigManager._is_within_usecli_package",
                return_value=False,
            ),
            patch(
                "usecli.shared.config.manager._get_high_level_dirs",
                return_value={str(tmp_path.resolve())},
            ),
        ):
            result = find_project_root(tmp_path)
        assert result is None


# ---------------------------------------------------------------------------
# _get_package_name
# ---------------------------------------------------------------------------


class TestGetPackageNameFallback:
    def test_returns_usecli_when_no_package(self):
        with (
            patch("usecli.shared.config.manager.__package__", ""),
            patch("usecli.shared.config.manager.__name__", ""),
        ):
            assert _get_package_name() == "usecli"
