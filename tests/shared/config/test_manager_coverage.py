"""Tests for project-root resolution edge cases in the config manager."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from usecli.shared.config.manager import (
    ConfigManager,
    find_project_root,
    reset_config,
    resolve_config_path,
)


@pytest.fixture(autouse=True)
def clean_caches():
    reset_config()
    yield
    reset_config()


class TestFindProjectRoot:
    def test_uses_console_script_config_match(self, tmp_path: Path) -> None:
        config = tmp_path / "configs" / "usecli.config.toml"
        config.parent.mkdir(parents=True)
        config.write_text("[usecli]\n")
        deep = tmp_path / "deep" / "nested"
        deep.mkdir(parents=True)
        with patch(
            "usecli.shared.config.manager.ConfigManager."
            "_find_usecli_config_for_console_script",
            return_value=config,
        ):
            root = find_project_root(deep)
        assert root == config.parent


class TestResolveConfigPath:
    def test_defaults_to_current_directory(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "usecli.config.toml").write_text("[usecli]\n")
        assert resolve_config_path() == tmp_path / "usecli.config.toml"


class TestVenvProjectRoot:
    def test_framework_root_resets_out_of_venv(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["/usr/local/bin/usecli"])
        site = tmp_path / "proj" / ".venv" / "venvs" / "site"
        nested = site / "sub"
        nested.mkdir(parents=True)
        (site / "usecli.config.toml").write_text("[usecli]\n")

        manager = ConfigManager(start_dir=nested)

        assert manager.project_root == nested.resolve()
        assert manager.project_root != site
