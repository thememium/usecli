"""Tests for ``[usecli.upgrade]`` settings parsing."""

from __future__ import annotations

from typing import Any

import pytest

from usecli.cli.core.exceptions.config import UsecliConfigError
from usecli.shared.upgrades.settings import UpgradeSettings, from_config


class FakeConfig:
    def __init__(self, values: dict[str, Any] | None = None) -> None:
        self.values = values or {}
        self.usecli_config_path = "/project/usecli.config.toml"

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)


class TestDefaults:
    def test_missing_config_uses_auto(self) -> None:
        assert from_config(None) == UpgradeSettings()

    def test_object_without_get_uses_auto(self) -> None:
        assert from_config(object()) == UpgradeSettings()

    def test_empty_section_uses_auto(self) -> None:
        assert from_config(FakeConfig()) == UpgradeSettings(source="auto")

    def test_explicit_none_source_uses_auto(self) -> None:
        assert from_config(FakeConfig({"upgrade.source": None})) == UpgradeSettings()

    def test_auto_does_not_override(self) -> None:
        assert (
            from_config(FakeConfig({"upgrade.source": "auto"})).overrides_source
            is False
        )


class TestParsing:
    def test_reads_all_overrides(self) -> None:
        settings = from_config(
            FakeConfig(
                {
                    "upgrade.source": "git",
                    "upgrade.package": " magic-cli ",
                    "upgrade.url": "https://github.com/foo/magic.git",
                    "upgrade.ref": "main",
                }
            )
        )
        assert settings == UpgradeSettings(
            source="git",
            package="magic-cli",
            url="https://github.com/foo/magic.git",
            ref="main",
        )
        assert settings.overrides_source is True

    def test_source_is_case_insensitive(self) -> None:
        assert from_config(FakeConfig({"upgrade.source": "PyPI"})).source == "pypi"

    def test_blank_strings_mean_unset(self) -> None:
        settings = from_config(
            FakeConfig(
                {
                    "upgrade.source": "git",
                    "upgrade.package": "  ",
                    "upgrade.url": "",
                }
            )
        )
        assert settings.package is None
        assert settings.url is None

    def test_non_string_values_are_ignored(self) -> None:
        settings = from_config(
            FakeConfig(
                {
                    "upgrade.source": "git",
                    "upgrade.package": 123,
                    "upgrade.ref": ["main"],
                }
            )
        )
        assert settings.package is None
        assert settings.ref is None


class TestValidation:
    def test_invalid_source_raises_with_context(self) -> None:
        with pytest.raises(UsecliConfigError) as error:
            from_config(FakeConfig({"upgrade.source": "github"}))
        assert "github" in str(error.value)
        assert error.value.config_file == "/project/usecli.config.toml"

    def test_blank_source_raises(self) -> None:
        with pytest.raises(UsecliConfigError):
            from_config(FakeConfig({"upgrade.source": "  "}))

    def test_non_string_source_raises(self) -> None:
        with pytest.raises(UsecliConfigError):
            from_config(FakeConfig({"upgrade.source": 1}))
