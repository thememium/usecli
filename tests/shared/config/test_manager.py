"""Tests for ConfigManager - pyproject.toml configuration."""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from usecli.cli.core.exceptions.config import UsecliConfigError
from usecli.shared.config import manager as config_manager
from usecli.shared.config.manager import (
    ConfigManager,
    _deep_merge,
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
        monkeypatch.setattr(
            config_manager.importlib.metadata,
            "distributions",
            lambda: [FakeDist("usechange")],
        )
        monkeypatch.setattr(sys, "argv", ["usechange"])

        manager = ConfigManager()

        assert manager.get("title") == "Package CLI"

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
