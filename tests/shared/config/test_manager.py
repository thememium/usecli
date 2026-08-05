"""Tests for ConfigManager - pyproject.toml configuration."""

from __future__ import annotations

import sys
import types
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from typing import ClassVar
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from usecli.cli.core.exceptions.config import UsecliConfigError
from usecli.shared.config import manager as config_manager
from usecli.shared.config.manager import (
    ConfigManager,
    _config_search_cache,
    _deep_merge,
    _find_distribution_for_console_script,
    _get_distributions,
    _get_package_name,
    _get_tomllib,
    _reset_distributions_cache,
    _reset_project_root_cache,
    _reset_toml_cache,
    _walk_for_filename,
    find_project_root,
    get_config,
    reset_config,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_project_dir(tmp_path, monkeypatch):
    """Fixture providing a temporary project directory."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def sample_config():
    """Sample configuration content."""
    return {
        "title": "My CLI",
        "description": "A test CLI",
        "commands_dir": "my_commands",
        "environment": "dev",
        "command_name": "mycli",
    }


# =============================================================================
# _deep_merge Tests
# =============================================================================


class TestDeepMerge:
    def test_merges_simple_keys(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"logging": {"level": "info", "file_enabled": False}}
        override = {"logging": {"level": "debug"}}
        result = _deep_merge(base, override)
        assert result == {"logging": {"level": "debug", "file_enabled": False}}


# =============================================================================
# ConfigManager Tests
# =============================================================================


class TestConfigManagerDefaults:
    def test_starts_with_defaults(self, temp_project_dir):
        manager = ConfigManager(
            usecli_config_path=temp_project_dir / "usecli.config.toml"
        )

        assert manager.get("title") == "usecli"
        assert manager.get("description") == "A customizable CLI framework"
        assert manager.get("commands_dir") == "cli/commands"
        assert manager.get("themes_dir") == ["cli/themes"]
        assert manager.get("environment") == "prod"
        assert manager.get("command_name") == "usecli"
        assert manager.get("hide_inspire") is False

    def test_default_environment_methods(self, temp_project_dir):
        manager = ConfigManager(
            usecli_config_path=temp_project_dir / "usecli.config.toml"
        )

        assert manager.is_prod() is True
        assert manager.is_dev() is False


class TestConfigManagerPyproject:
    def test_loads_from_pyproject_toml(self, temp_project_dir):
        config_file = temp_project_dir / "usecli.config.toml"
        config_file.write_text(
            """
[usecli]
title = "My Project CLI"
description = "Custom CLI"
commands_dir = "custom_cmds"
"""
        )

        manager = ConfigManager()

        assert manager.get("title") == "My Project CLI"
        assert manager.get("description") == "Custom CLI"
        assert manager.get("commands_dir") == "custom_cmds"

    def test_loads_from_nested_usecli_config(self, temp_project_dir):
        nested_dir = temp_project_dir / "package" / "config"
        nested_dir.mkdir(parents=True)
        config_file = nested_dir / "usecli.config.toml"
        config_file.write_text(
            """
[usecli]
title = "Nested CLI"
description = "Nested config"
commands_dir = "nested/commands"
"""
        )

        manager = ConfigManager()

        assert manager.get("title") == "Nested CLI"
        assert manager.get("description") == "Nested config"
        assert manager.get("commands_dir") == "nested/commands"
        assert manager.get_project_root() == nested_dir

    def test_prefers_project_config_over_package(self, temp_project_dir, monkeypatch):
        project_config = temp_project_dir / "usecli.config.toml"
        project_config.write_text(
            """
[usecli]
title = "Project CLI"
description = "Project config"
"""
        )

        package_root = temp_project_dir / ".venv" / "lib" / "site-packages" / "usecli"
        package_config_dir = package_root / "cli"
        package_config_dir.mkdir(parents=True)
        package_config = package_config_dir / "usecli.config.toml"
        package_config.write_text(
            """
[usecli]
title = "Package CLI"
description = "Package config"
"""
        )

        spec = types.SimpleNamespace(submodule_search_locations=[str(package_root)])
        monkeypatch.setattr(
            config_manager.importlib.util, "find_spec", lambda name: spec
        )

        manager = ConfigManager()

        assert manager.get("title") == "Project CLI"

    def test_loads_from_usecli_toml_when_pyproject_missing(self, temp_project_dir):
        config_file = temp_project_dir / "usecli.config.toml"
        config_file.write_text(
            """
[usecli]
title = "My CLI"
description = "Config file"
commands_dir = "pkg/commands"
"""
        )

        manager = ConfigManager()

        assert manager.get("title") == "My CLI"
        assert manager.get("description") == "Config file"
        assert manager.get("commands_dir") == "pkg/commands"

    def test_pyproject_takes_precedence_over_defaults(self, temp_project_dir):
        config_file = temp_project_dir / "usecli.config.toml"
        config_file.write_text('[usecli]\nenvironment = "dev"')

        manager = ConfigManager()

        assert manager.get("environment") == "dev"
        assert manager.is_dev() is True

    def test_themes_dir_merges_without_duplicates(self, temp_project_dir):
        config_file = temp_project_dir / "usecli.config.toml"
        config_file.write_text(
            """
[usecli]
themes_dir = ["custom/themes", "cli/themes", "custom/themes"]
"""
        )

        manager = ConfigManager()

        assert manager.get("themes_dir") == ["cli/themes", "custom/themes"]

    def test_pyproject_exists_property(self, temp_project_dir):
        config_file = temp_project_dir / "usecli.config.toml"
        config_file.write_text('[usecli]\ntitle = "Test"')

        manager = ConfigManager()

        assert manager.pyproject_exists is True

    def test_pyproject_exists_with_usecli_toml(self, temp_project_dir):
        config_file = temp_project_dir / "usecli.config.toml"
        config_file.write_text('[usecli]\ntitle = "Test"')

        manager = ConfigManager()

        assert manager.pyproject_exists is True

    def test_pyproject_exists_false_without_tool_section(self, temp_project_dir):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[project]\nname = "other"')

        manager = ConfigManager(
            usecli_config_path=temp_project_dir / "usecli.config.toml"
        )

        assert manager.pyproject_exists is False

    def test_nested_config_overrides_pyproject_root(self, temp_project_dir):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[project]\nname = "sample"')

        nested_dir = temp_project_dir / "pkg" / "cli"
        nested_dir.mkdir(parents=True)
        config_file = nested_dir / "usecli.config.toml"
        config_file.write_text('[usecli]\ntitle = "Nested CLI"')

        manager = ConfigManager()

        assert manager.get_project_root() == nested_dir

    def test_console_script_package_config_selected(
        self, temp_project_dir, monkeypatch
    ):
        package_root = temp_project_dir / "site-packages" / "usechange"
        package_cli = package_root / "cli"
        package_cli.mkdir(parents=True)
        package_config = package_cli / "usecli.config.toml"
        package_config.write_text('[usecli]\ntitle = "Package CLI"')

        class FakeEntryPoint:
            def __init__(self, name: str) -> None:
                self.group = "console_scripts"
                self.name = name

        class FakeDist:
            def __init__(self, name: str) -> None:
                self.metadata = {"Name": name}
                self.entry_points = [FakeEntryPoint("usechange")]

        spec = types.SimpleNamespace(submodule_search_locations=[str(package_root)])
        monkeypatch.setattr(
            config_manager.importlib.util, "find_spec", lambda name: spec
        )
        _reset_distributions_cache()
        monkeypatch.setattr(
            config_manager.importlib.metadata,
            "distributions",
            lambda: [FakeDist("usechange")],
        )
        monkeypatch.setattr(sys, "argv", ["usechange"])

        manager = ConfigManager()

        assert manager.get("title") == "Package CLI"

    def test_console_script_finds_config_via_top_level_txt(
        self, temp_project_dir, monkeypatch
    ):
        package_root = temp_project_dir / "site-packages" / "cli"
        package_root.mkdir(parents=True)
        package_config = package_root / "usecli.config.toml"
        package_config.write_text('[usecli]\ntitle = "Scaffolded CLI"')

        class FakeEntryPoint:
            def __init__(self, name: str) -> None:
                self.group = "console_scripts"
                self.name = name

        class FakeDist:
            def __init__(self, name: str) -> None:
                self.metadata = {"Name": name}
                self.entry_points = [FakeEntryPoint("magic")]

            def read_text(self, filename: str) -> str | None:
                if filename == "top_level.txt":
                    return "cli"
                return None

        def fake_find_spec(name: str):
            if name == "cli":
                return types.SimpleNamespace(
                    submodule_search_locations=[str(package_root)]
                )
            return None

        monkeypatch.setattr(config_manager.importlib.util, "find_spec", fake_find_spec)
        _reset_distributions_cache()
        monkeypatch.setattr(
            config_manager.importlib.metadata,
            "distributions",
            lambda: [FakeDist("2026-07-25-newusecli")],
        )
        monkeypatch.setattr(sys, "argv", ["magic"])

        manager = ConfigManager()

        assert manager.get("title") == "Scaffolded CLI"

    def test_console_script_ignores_mismatched_project_config(
        self, temp_project_dir, monkeypatch
    ):
        project_config = temp_project_dir / "usecli.config.toml"
        project_config.write_text(
            """
[usecli]
title = "Project CLI"
command_name = "usecli"
"""
        )

        package_root = temp_project_dir / "site-packages" / "usechange"
        package_cli = package_root / "cli"
        package_cli.mkdir(parents=True)
        package_config = package_cli / "usecli.config.toml"
        package_config.write_text(
            '[usecli]\ntitle = "Package CLI"\ncommand_name = "usechange"'
        )

        class FakeEntryPoint:
            def __init__(self, name: str) -> None:
                self.group = "console_scripts"
                self.name = name

        class FakeDist:
            def __init__(self, name: str) -> None:
                self.metadata = {"Name": name}
                self.entry_points = [FakeEntryPoint("usechange")]

        spec = types.SimpleNamespace(submodule_search_locations=[str(package_root)])
        monkeypatch.setattr(
            config_manager.importlib.util, "find_spec", lambda name: spec
        )
        _reset_distributions_cache()
        monkeypatch.setattr(
            config_manager.importlib.metadata,
            "distributions",
            lambda: [FakeDist("usechange")],
        )
        monkeypatch.setattr(sys, "argv", ["usechange"])

        manager = ConfigManager()

        assert manager.get("title") == "Package CLI"

    def test_console_script_alias_selects_package_config(
        self, temp_project_dir, monkeypatch
    ):
        package_root = temp_project_dir / "site-packages" / "usechange"
        package_cli = package_root / "cli"
        package_cli.mkdir(parents=True)
        package_config = package_cli / "usecli.config.toml"
        package_config.write_text(
            '[usecli]\ntitle = "Package CLI"\ncommand_name = "usechange"'
        )

        class FakeEntryPoint:
            def __init__(self, name: str) -> None:
                self.group = "console_scripts"
                self.name = name

        class FakeDist:
            def __init__(self, name: str) -> None:
                self.metadata = {"Name": name}
                self.entry_points = [
                    FakeEntryPoint("usechange"),
                    FakeEntryPoint("change"),
                ]

        spec = types.SimpleNamespace(submodule_search_locations=[str(package_root)])
        monkeypatch.setattr(
            config_manager.importlib.util, "find_spec", lambda name: spec
        )
        _reset_distributions_cache()
        monkeypatch.setattr(
            config_manager.importlib.metadata,
            "distributions",
            lambda: [FakeDist("usechange")],
        )
        monkeypatch.setattr(sys, "argv", ["change"])

        manager = ConfigManager()

        assert manager.get("title") == "Package CLI"


class TestConfigManagerErrors:
    def test_raises_on_invalid_pyproject_toml(self, temp_project_dir):
        config_file = temp_project_dir / "usecli.config.toml"
        config_file.write_text("[invalid toml")

        with pytest.raises(UsecliConfigError) as exc_info:
            ConfigManager()

        assert "usecli.config.toml" in str(exc_info.value).lower()


class TestConfigManagerGetMethods:
    def test_get_dot_notation(self, temp_project_dir):
        config_file = temp_project_dir / "usecli.config.toml"
        config_file.write_text("""
[usecli.logging]
level = "debug"
file_enabled = true
""")

        manager = ConfigManager()

        assert manager.get("logging.level") == "debug"
        assert manager.get("logging.file_enabled") is True

    def test_get_returns_default(self, temp_project_dir):
        manager = ConfigManager()

        assert manager.get("nonexistent") is None
        assert manager.get("nonexistent", "default") == "default"

    def test_get_all_returns_copy(self, temp_project_dir):
        config_file = temp_project_dir / "usecli.config.toml"
        config_file.write_text('[usecli]\ntitle = "Test"')

        manager = ConfigManager()
        all_config = manager.get_all()

        # Modifying returned dict shouldn't affect manager
        all_config["new_key"] = "new_value"
        assert manager.get("new_key") is None


class TestConfigManagerReload:
    def test_reload_picks_up_changes(self, temp_project_dir):
        manager = ConfigManager(
            usecli_config_path=temp_project_dir / "usecli.config.toml"
        )
        assert manager.get("title") == "usecli"

        # Add config after initialization
        config_file = temp_project_dir / "usecli.config.toml"
        config_file.write_text('[usecli]\ntitle = "Updated"')

        # Reload and verify
        manager.reload()
        assert manager.get("title") == "Updated"


# =============================================================================
# Singleton Tests
# =============================================================================


class TestConfigSingleton:
    def test_get_config_returns_same_instance(self, temp_project_dir):
        reset_config()

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_reset_config_creates_new_instance(self, temp_project_dir):
        reset_config()
        config1 = get_config()

        reset_config()
        config2 = get_config()

        assert config1 is not config2

    def test_get_config_refreshes_on_root_change(self, temp_project_dir, monkeypatch):
        reset_config()
        (temp_project_dir / "usecli.config.toml").write_text(
            '[usecli]\ntitle = "First"'
        )

        config1 = get_config()
        assert config1.get("title") == "First"

        other_root = temp_project_dir / "other"
        other_root.mkdir()
        (other_root / "usecli.config.toml").write_text('[usecli]\ntitle = "Second"')
        monkeypatch.chdir(other_root)

        config2 = get_config()
        assert config2.get("title") == "Second"
        assert config1 is not config2


# =============================================================================
# Coverage-focused: config discovery, TOML loading, validation, fallbacks
# =============================================================================


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

    def test_explicit_config_path_skips_discovery(self, tmp_path):
        config = tmp_path / "usecli.config.toml"
        config.write_text('[usecli]\ntitle = "x"')
        with patch("usecli.shared.config.manager.find_project_root") as mock_fpr:
            manager = ConfigManager(usecli_config_path=config, start_dir=tmp_path)
        # An explicit config path is authoritative: no filesystem discovery runs.
        mock_fpr.assert_not_called()
        # The project root is derived from the config's own directory.
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
