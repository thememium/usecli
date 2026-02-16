"""Tests for ConfigManager - configuration management with global and local config support."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

# Add src to path for imports
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
def temp_config_dirs(tmp_path, monkeypatch):
    """Fixture providing temporary global and local config directories."""
    global_dir = tmp_path / ".config" / "usecli"
    global_dir.mkdir(parents=True)
    global_config = global_dir / "config.yaml"

    local_dir = tmp_path / "usecli"
    local_dir.mkdir(parents=True)
    local_config = local_dir / "config.yaml"

    monkeypatch.chdir(tmp_path)

    return {
        "global_dir": global_dir,
        "global_config": global_config,
        "local_dir": local_dir,
        "local_config": local_config,
        "base_path": tmp_path,
    }


@pytest.fixture
def sample_global_config():
    """Fixture providing sample global configuration content."""
    return {
        "environment": "dev",
        "logging": {
            "level": "info",
            "file_enabled": False,
            "file_path": "usecli.log",
        },
        "features": {"auto_update_check": True, "analytics": False},
        "defaults": {"editor": "vim", "assistant": "auto"},
    }


@pytest.fixture
def sample_local_config():
    """Fixture providing sample local configuration content."""
    return {
        "environment": "prod",
        "logging": {"level": "debug"},
        "features": {"analytics": True},
    }


# =============================================================================
# _deep_merge Tests
# =============================================================================


class TestDeepMerge:
    """Tests for the _deep_merge helper function."""

    def test_merges_simple_keys(self):
        """Test that _deep_merge correctly merges simple key-value pairs."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        """Test that _deep_merge correctly merges nested dictionaries."""
        base = {"logging": {"level": "info", "file_enabled": False}}
        override = {"logging": {"level": "debug"}}
        result = _deep_merge(base, override)
        assert result == {"logging": {"level": "debug", "file_enabled": False}}

    def test_deeply_nested_merge(self):
        """Test merging of deeply nested structures."""
        base = {"a": {"b": {"c": 1, "d": 2}}}
        override = {"a": {"b": {"d": 3, "e": 4}}}
        result = _deep_merge(base, override)
        assert result == {"a": {"b": {"c": 1, "d": 3, "e": 4}}}

    def test_override_replaces_nested_dict(self):
        """Test that non-dict values completely replace."""
        base = {"logging": {"level": "info"}}
        override = {"logging": "disabled"}
        result = _deep_merge(base, override)
        assert result == {"logging": "disabled"}

    def test_empty_override(self):
        """Test merging with empty override."""
        base = {"a": 1, "b": 2}
        override = {}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 2}

    def test_empty_base(self):
        """Test merging with empty base."""
        base = {}
        override = {"a": 1, "b": 2}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 2}


# =============================================================================
# ConfigManager Initialization Tests
# =============================================================================


class TestConfigManagerInit:
    """Tests for ConfigManager initialization."""

    def test_uses_default_paths(self, tmp_path, monkeypatch):
        """Test ConfigManager uses default paths when none provided."""
        monkeypatch.chdir(tmp_path)
        manager = ConfigManager()

        assert (
            manager.global_config_path
            == Path.home() / ".config" / "usecli" / "config.yaml"
        )
        assert manager.local_config_path == tmp_path / "usecli" / "config.yaml"

    def test_uses_provided_paths(self, tmp_path):
        """Test ConfigManager uses provided paths."""
        global_path = tmp_path / "global.yaml"
        local_path = tmp_path / "local.yaml"

        manager = ConfigManager(global_path, local_path)

        assert manager.global_config_path == global_path
        assert manager.local_config_path == local_path

    def test_starts_with_defaults(self, tmp_path, monkeypatch):
        """Test ConfigManager starts with default values."""
        monkeypatch.chdir(tmp_path)

        # Use explicit non-existent paths to ensure defaults are used
        manager = ConfigManager(
            global_config_path=tmp_path / "nonexistent" / "global.yaml",
            local_config_path=tmp_path / "nonexistent" / "local.yaml",
        )

        assert manager.get("environment") == "prod"
        assert manager.get("logging.level") == "info"
        assert manager.get("features.auto_update_check") is True

    def test_loads_global_config(self, temp_config_dirs, sample_global_config):
        """Test ConfigManager loads global config."""
        # Write global config
        with open(temp_config_dirs["global_config"], "w") as f:
            yaml.dump(sample_global_config, f)

        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.get("environment") == "dev"
        assert manager.get("logging.level") == "info"

    def test_loads_local_config(self, temp_config_dirs, sample_local_config):
        """Test ConfigManager loads local config."""
        # Write local config
        with open(temp_config_dirs["local_config"], "w") as f:
            yaml.dump(sample_local_config, f)

        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        # Local config should override defaults
        assert manager.get("environment") == "prod"
        assert manager.get("logging.level") == "debug"

    def test_local_overrides_global(
        self, temp_config_dirs, sample_global_config, sample_local_config
    ):
        """Test local config values override global config."""
        # Write both configs
        with open(temp_config_dirs["global_config"], "w") as f:
            yaml.dump(sample_global_config, f)

        with open(temp_config_dirs["local_config"], "w") as f:
            yaml.dump(sample_local_config, f)

        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        # Local values should take precedence
        assert manager.get("environment") == "prod"
        assert manager.get("logging.level") == "debug"
        # Global values not in local should remain
        assert manager.get("logging.file_path") == "usecli.log"
        assert manager.get("defaults.editor") == "vim"

    def test_handles_missing_global_config(self, temp_config_dirs):
        """Test ConfigManager handles missing global config gracefully."""
        # Don't create global config
        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        # Should use defaults
        assert manager.get("environment") == "prod"
        assert not manager.global_config_exists

    def test_handles_missing_local_config(self, temp_config_dirs, sample_global_config):
        """Test ConfigManager handles missing local config gracefully."""
        # Write only global config
        with open(temp_config_dirs["global_config"], "w") as f:
            yaml.dump(sample_global_config, f)

        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        # Should use global values
        assert manager.get("environment") == "dev"
        assert manager.global_config_exists
        assert not manager.local_config_exists


# =============================================================================
# ConfigManager Error Handling Tests
# =============================================================================


class TestConfigManagerErrors:
    """Tests for ConfigManager error handling."""

    def test_raises_on_invalid_global_yaml(self, temp_config_dirs):
        """Test ConfigManager raises on invalid global YAML."""
        # Write invalid YAML
        temp_config_dirs["global_config"].write_text("invalid: [yaml: content")

        with pytest.raises(UsecliConfigError) as exc_info:
            ConfigManager(
                global_config_path=temp_config_dirs["global_config"],
                local_config_path=temp_config_dirs["local_config"],
            )

        assert "global config" in str(exc_info.value).lower()
        assert str(temp_config_dirs["global_config"]) in str(exc_info.value)

    def test_raises_on_invalid_local_yaml(self, temp_config_dirs, sample_global_config):
        """Test ConfigManager raises on invalid local YAML."""
        # Write valid global but invalid local
        with open(temp_config_dirs["global_config"], "w") as f:
            yaml.dump(sample_global_config, f)

        temp_config_dirs["local_config"].write_text("invalid: [yaml: content")

        with pytest.raises(UsecliConfigError) as exc_info:
            ConfigManager(
                global_config_path=temp_config_dirs["global_config"],
                local_config_path=temp_config_dirs["local_config"],
            )

        assert "local config" in str(exc_info.value).lower()
        assert str(temp_config_dirs["local_config"]) in str(exc_info.value)

    def test_raises_on_non_dict_yaml(self, temp_config_dirs):
        """Test ConfigManager raises when YAML doesn't contain a dict."""
        temp_config_dirs["global_config"].write_text("- list item 1\n- list item 2")

        with pytest.raises(UsecliConfigError):
            ConfigManager(
                global_config_path=temp_config_dirs["global_config"],
                local_config_path=temp_config_dirs["local_config"],
            )

    def test_handles_empty_yaml_file(self, temp_config_dirs):
        """Test ConfigManager handles empty YAML file."""
        temp_config_dirs["global_config"].write_text("")

        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        # Should use defaults
        assert manager.get("environment") == "prod"


# =============================================================================
# ConfigManager Get Method Tests
# =============================================================================


class TestConfigManagerGet:
    """Tests for ConfigManager.get() method."""

    def test_get_simple_key(self, temp_config_dirs, sample_global_config):
        """Test getting a simple top-level key."""
        with open(temp_config_dirs["global_config"], "w") as f:
            yaml.dump(sample_global_config, f)

        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.get("environment") == "dev"

    def test_get_nested_key(self, temp_config_dirs, sample_global_config):
        """Test getting a nested key using dot notation."""
        with open(temp_config_dirs["global_config"], "w") as f:
            yaml.dump(sample_global_config, f)

        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.get("logging.level") == "info"
        assert manager.get("features.auto_update_check") is True

    def test_get_returns_default_for_missing_key(self, temp_config_dirs):
        """Test get returns default for missing key."""
        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.get("nonexistent.key") is None
        assert manager.get("nonexistent.key", "default") == "default"

    def test_get_returns_default_for_deeply_nested_missing_key(self, temp_config_dirs):
        """Test get returns default for deeply nested missing key."""
        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.get("logging.nonexistent.nested") is None

    def test_get_all_returns_copy(self, temp_config_dirs, sample_global_config):
        """Test get_all returns a copy, not the original."""
        with open(temp_config_dirs["global_config"], "w") as f:
            yaml.dump(sample_global_config, f)

        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        all_config = manager.get_all()
        all_config["new_key"] = "new_value"

        # Original should be unchanged
        assert "new_key" not in manager.get_all()


# =============================================================================
# ConfigManager Environment Tests
# =============================================================================


class TestConfigManagerEnvironment:
    """Tests for environment detection methods."""

    def test_is_dev_returns_true_for_dev(self, temp_config_dirs):
        """Test is_dev returns True when environment is dev."""
        temp_config_dirs["global_config"].write_text('environment: "dev"')

        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.is_dev() is True
        assert manager.is_prod() is False

    def test_is_prod_returns_true_for_prod(self, temp_config_dirs):
        """Test is_prod returns True when environment is prod."""
        temp_config_dirs["global_config"].write_text('environment: "prod"')

        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.is_prod() is True
        assert manager.is_dev() is False

    def test_defaults_to_prod(self, temp_config_dirs):
        """Test environment defaults to prod when not specified."""
        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.is_dev() is False
        assert manager.is_prod() is True

    def test_handles_unusual_environment_values(self, temp_config_dirs):
        """Test handles unusual environment values gracefully."""
        temp_config_dirs["global_config"].write_text('environment: "staging"')

        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        # Neither dev nor prod
        assert manager.is_dev() is False
        assert manager.is_prod() is False


# =============================================================================
# ConfigManager Reload Tests
# =============================================================================


class TestConfigManagerReload:
    """Tests for ConfigManager.reload() method."""

    def test_reload_picks_up_new_global_config(self, temp_config_dirs):
        """Test reload picks up changes to global config."""
        # Start with no config
        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.get("environment") == "prod"

        # Add global config with dev environment
        temp_config_dirs["global_config"].write_text('environment: "dev"')

        # Reload and check
        manager.reload()
        assert manager.get("environment") == "dev"

    def test_reload_picks_up_new_local_config(self, temp_config_dirs):
        """Test reload picks up changes to local config."""
        # Start with no local config
        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.get("environment") == "prod"

        # Add local config with dev environment
        temp_config_dirs["local_config"].write_text('environment: "dev"')

        # Reload and check
        manager.reload()
        assert manager.get("environment") == "dev"


# =============================================================================
# ConfigManager Existence Properties Tests
# =============================================================================


class TestConfigManagerExistence:
    """Tests for global_config_exists and local_config_exists properties."""

    def test_global_config_exists_false_when_missing(self, temp_config_dirs):
        """Test global_config_exists is False when file doesn't exist."""
        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.global_config_exists is False

    def test_global_config_exists_true_when_present(self, temp_config_dirs):
        """Test global_config_exists is True when file exists."""
        temp_config_dirs["global_config"].write_text("environment: dev")

        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.global_config_exists is True

    def test_local_config_exists_false_when_missing(self, temp_config_dirs):
        """Test local_config_exists is False when file doesn't exist."""
        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.local_config_exists is False

    def test_local_config_exists_true_when_present(self, temp_config_dirs):
        """Test local_config_exists is True when file exists."""
        temp_config_dirs["local_config"].write_text("environment: prod")

        manager = ConfigManager(
            global_config_path=temp_config_dirs["global_config"],
            local_config_path=temp_config_dirs["local_config"],
        )

        assert manager.local_config_exists is True


# =============================================================================
# Singleton Tests
# =============================================================================


class TestConfigSingleton:
    """Tests for get_config() and reset_config() singleton functions."""

    def test_get_config_returns_same_instance(self, tmp_path, monkeypatch):
        """Test get_config returns the same ConfigManager instance."""
        monkeypatch.chdir(tmp_path)

        # Reset any previous singleton
        reset_config()

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_reset_config_creates_new_instance(self, tmp_path, monkeypatch):
        """Test reset_config forces creation of new instance."""
        monkeypatch.chdir(tmp_path)

        # Reset and get first instance
        reset_config()
        config1 = get_config()

        # Reset and get second instance
        reset_config()
        config2 = get_config()

        assert config1 is not config2

    def test_reset_config_affects_future_get_config_calls(self, tmp_path, monkeypatch):
        """Test reset_config affects future get_config calls."""
        monkeypatch.chdir(tmp_path)

        reset_config()

        # Create initial config file with dev environment
        global_config = Path.home() / ".config" / "usecli" / "config.yaml"
        global_config.parent.mkdir(parents=True, exist_ok=True)
        global_config.write_text('environment: "dev"')

        config_before = get_config()
        assert config_before.get("environment") == "dev"

        # Update config to prod
        global_config.write_text('environment: "prod"')

        reset_config()
        config_after = get_config()

        # Should pick up new config
        assert config_after.get("environment") == "prod"
