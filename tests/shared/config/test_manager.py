"""Tests for ConfigManager - simplified TOML-only configuration."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from usecli.cli.core.exceptions.config import UsecliConfigError
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
        manager = ConfigManager()

        assert manager.get("title") == "usecli"
        assert manager.get("description") == "A customizable CLI framework"
        assert manager.get("commands_dir") == "cli/commands"
        assert manager.get("environment") == "prod"
        assert manager.get("command_name") == "usecli"
        assert manager.get("hide_init") is False
        assert manager.get("hide_inspire") is False
        assert manager.get("hide_make_command") is False

    def test_default_environment_methods(self, temp_project_dir):
        manager = ConfigManager()

        assert manager.is_prod() is True
        assert manager.is_dev() is False


class TestConfigManagerPyproject:
    def test_loads_from_pyproject_toml(self, temp_project_dir):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text("""
[tool.usecli]
title = "My Project CLI"
description = "Custom CLI"
commands_dir = "custom_cmds"
""")

        manager = ConfigManager()

        assert manager.get("title") == "My Project CLI"
        assert manager.get("description") == "Custom CLI"
        assert manager.get("commands_dir") == "custom_cmds"

    def test_pyproject_takes_precedence_over_defaults(self, temp_project_dir):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[tool.usecli]\nenvironment = "dev"')

        manager = ConfigManager()

        assert manager.get("environment") == "dev"
        assert manager.is_dev() is True

    def test_pyproject_exists_property(self, temp_project_dir):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[tool.usecli]\ntitle = "Test"')

        manager = ConfigManager()

        assert manager.pyproject_exists is True

    def test_pyproject_exists_false_without_tool_section(self, temp_project_dir):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[project]\nname = "other"')

        manager = ConfigManager()

        assert manager.pyproject_exists is False


class TestConfigManagerStandaloneToml:
    def test_loads_from_usecli_config_toml(self, temp_project_dir):
        config = temp_project_dir / "usecli.config.toml"
        config.write_text("""
[usecli]
title = "Standalone Config"
description = "From standalone file"
commands_dir = "standalone_cmds"
""")

        manager = ConfigManager()

        assert manager.get("title") == "Standalone Config"
        assert manager.get("commands_dir") == "standalone_cmds"

    def test_finds_config_in_parent_directory(self, temp_project_dir):
        # Create config in parent
        config = temp_project_dir / "usecli.config.toml"
        config.write_text('[usecli]\ntitle = "Parent Config"')

        # Create subdirectory and cd into it
        subdir = temp_project_dir / "subdir"
        subdir.mkdir()

        manager = ConfigManager(start_dir=subdir)

        assert manager.get("title") == "Parent Config"

    def test_config_toml_path_property(self, temp_project_dir):
        config = temp_project_dir / "usecli.config.toml"
        config.write_text('[usecli]\ntitle = "Test"')

        manager = ConfigManager()

        assert manager.config_toml_path == config

    def test_config_toml_path_none_when_not_found(self, temp_project_dir):
        manager = ConfigManager()

        assert manager.config_toml_path is None


class TestConfigManagerPriority:
    def test_pyproject_overrides_usecli_config_toml(self, temp_project_dir):
        # Create standalone config
        standalone = temp_project_dir / "usecli.config.toml"
        standalone.write_text('[usecli]\ntitle = "Standalone"\ncommands_dir = "dir1"')

        # Create pyproject with conflicting values
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text(
            '[tool.usecli]\ntitle = "PyProject"\ncommands_dir = "dir2"'
        )

        manager = ConfigManager()

        # pyproject values should win
        assert manager.get("title") == "PyProject"
        assert manager.get("commands_dir") == "dir2"

    def test_merged_config_keeps_unique_values(self, temp_project_dir):
        standalone = temp_project_dir / "usecli.config.toml"
        standalone.write_text('[usecli]\ncommand_name = "mycli"')

        # pyproject has title
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[tool.usecli]\ntitle = "Merged"')

        manager = ConfigManager()

        # Should have both values
        assert manager.get("title") == "Merged"
        assert manager.get("command_name") == "mycli"


class TestConfigManagerErrors:
    def test_raises_on_invalid_pyproject_toml(self, temp_project_dir):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text("[invalid toml")

        with pytest.raises(UsecliConfigError) as exc_info:
            ConfigManager()

        assert "pyproject.toml" in str(exc_info.value).lower()

    def test_raises_on_invalid_config_toml(self, temp_project_dir):
        config = temp_project_dir / "usecli.config.toml"
        config.write_text("[invalid toml")

        with pytest.raises(UsecliConfigError) as exc_info:
            ConfigManager()

        assert "usecli.config.toml" in str(exc_info.value).lower()


class TestConfigManagerGetMethods:
    def test_get_dot_notation(self, temp_project_dir):
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text("""
[tool.usecli.logging]
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
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[tool.usecli]\ntitle = "Test"')

        manager = ConfigManager()
        all_config = manager.get_all()

        # Modifying returned dict shouldn't affect manager
        all_config["new_key"] = "new_value"
        assert manager.get("new_key") is None


class TestConfigManagerReload:
    def test_reload_picks_up_changes(self, temp_project_dir):
        manager = ConfigManager()
        assert manager.get("title") == "usecli"

        # Add config after initialization
        pyproject = temp_project_dir / "pyproject.toml"
        pyproject.write_text('[tool.usecli]\ntitle = "Updated"')

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
