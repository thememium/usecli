"""Tests for install discovery from packaging metadata."""

from __future__ import annotations

import json
import sys
from importlib.metadata import version
from typing import Any
from unittest.mock import patch

import pytest

from usecli.shared.config.manager import reset_config
from usecli.shared.upgrades.discovery import InstallInfo, _revision_kind, discover


class FakeDist:
    """Minimal stand-in for an importlib.metadata Distribution."""

    metadata: Any

    def __init__(
        self,
        name: str = "magic-cli",
        version: str = "1.4.2",
        files: dict[str, Any] | None = None,
    ) -> None:
        self.metadata = {"Name": name}
        self.version = version
        self._files = files or {}

    def read_text(self, name: str) -> str | None:
        return self._files.get(name)


class FakeConfig:
    def __init__(self, version: str = "9.9.9") -> None:
        self._version = version

    def get_project_version(self) -> str:
        return self._version


def _direct_url(payload: dict[str, Any]) -> str:
    return json.dumps(payload)


def _install(fake_dist: FakeDist | None) -> InstallInfo:
    with (
        patch(
            "usecli.shared.upgrades.discovery._find_distribution_for_console_script",
            return_value=fake_dist,
        ),
        patch(
            "usecli.cli.core.ui.title.get_script_command_name",
            return_value=None,
        ),
    ):
        return discover(config=FakeConfig())


class TestIndexInstalls:
    def test_registry_install_is_index(self) -> None:
        dist = FakeDist(files={"INSTALLER": "uv\n"})
        install = _install(dist)
        assert install.source == "index"
        assert install.package == "magic-cli"
        assert install.version == "1.4.2"
        assert install.installer == "uv"
        assert install.pinned is False

    def test_pip_install_is_index(self) -> None:
        dist = FakeDist(files={"INSTALLER": "pip\n"})
        install = _install(dist)
        assert install.source == "index"
        assert install.installer == "pip"

    def test_missing_installer_file_is_index(self) -> None:
        install = _install(FakeDist())
        assert install.source == "index"
        assert install.installer is None

    def test_corrupt_direct_url_falls_back_to_index(self) -> None:
        dist = FakeDist(files={"direct_url.json": "{not json"})
        install = _install(dist)
        assert install.source == "index"


class TestGitInstalls:
    def test_branch_install_is_not_pinned(self) -> None:
        dist = FakeDist(
            files={
                "INSTALLER": "uv\n",
                "direct_url.json": _direct_url(
                    {
                        "url": "https://github.com/foo/magic.git",
                        "vcs_info": {
                            "vcs": "git",
                            "requested_revision": "main",
                            "commit_id": "abc123" + "0" * 34,
                        },
                    }
                ),
            }
        )
        install = _install(dist)
        assert install.source == "git"
        assert install.url == "https://github.com/foo/magic.git"
        assert install.revision == "main"
        assert install.commit is not None
        assert install.pinned is False

    def test_tag_install_is_pinned(self) -> None:
        dist = FakeDist(
            files={
                "direct_url.json": _direct_url(
                    {
                        "url": "https://github.com/foo/magic.git",
                        "vcs_info": {
                            "vcs": "git",
                            "requested_revision": "v1.2.0",
                            "commit_id": "abc123" + "0" * 34,
                        },
                    }
                )
            }
        )
        install = _install(dist)
        assert install.source == "git"
        assert install.pinned is True
        assert install.pinned_reason is not None
        assert "tag" in install.pinned_reason

    def test_commit_install_is_pinned(self) -> None:
        sha = "d34db33f" * 5
        dist = FakeDist(
            files={
                "direct_url.json": _direct_url(
                    {
                        "url": "https://github.com/foo/magic.git",
                        "vcs_info": {
                            "vcs": "git",
                            "requested_revision": sha,
                            "commit_id": sha,
                        },
                    }
                )
            }
        )
        install = _install(dist)
        assert install.source == "git"
        assert install.pinned is True
        assert install.pinned_reason is not None
        assert "commit" in install.pinned_reason

    def test_non_git_vcs_is_pinned_url(self) -> None:
        dist = FakeDist(
            files={
                "direct_url.json": _direct_url(
                    {
                        "url": "hg+https://hg.example.com/foo/magic",
                        "vcs_info": {"vcs": "hg"},
                    }
                )
            }
        )
        install = _install(dist)
        assert install.source == "url"
        assert install.pinned is True


class TestOtherInstalls:
    def test_editable_install(self) -> None:
        dist = FakeDist(
            files={
                "INSTALLER": "uv\n",
                "direct_url.json": _direct_url(
                    {
                        "url": "file:///home/dev/projects/magic",
                        "dir_info": {"editable": True},
                    }
                ),
            }
        )
        install = _install(dist)
        assert install.source == "editable"
        assert install.pinned is True
        assert install.pinned_reason == "editable install"

    def test_direct_url_install_is_pinned(self) -> None:
        dist = FakeDist(
            files={
                "direct_url.json": _direct_url(
                    {"url": "https://example.com/wheels/magic-1.0-py3-none-any.whl"}
                )
            }
        )
        install = _install(dist)
        assert install.source == "url"
        assert install.pinned is True
        assert install.pinned_reason == "direct URL install"


class TestUnidentifiedInstalls:
    def test_no_distribution_is_unknown_and_pinned(self) -> None:
        install = _install(None)
        assert install.source == "unknown"
        assert install.pinned is True
        assert install.version == "9.9.9"

    def test_frozen_bundle_is_unknown_and_pinned(self) -> None:
        with (
            patch(
                "usecli.shared.upgrades.discovery._find_distribution_for_console_script",
                return_value=FakeDist(),
            ),
            patch.object(sys, "frozen", True, create=True),
        ):
            install = discover(config=FakeConfig())
        assert install.frozen is True
        assert install.source == "unknown"
        assert install.pinned is True


class TestRevisionKind:
    @pytest.mark.parametrize(
        ("revision", "expected"),
        [
            (None, None),
            ("main", "branch"),
            ("develop", "branch"),
            ("release-2", "branch"),
            ("v1", "tag"),
            ("1.2.3", "tag"),
            ("v1.2.0", "tag"),
            ("d34db33", "commit"),
            ("d34db33f" * 5, "commit"),
        ],
    )
    def test_classification(self, revision: str | None, expected: str | None) -> None:
        assert _revision_kind(revision) == expected

    def test_whitespace_revision_is_unclassified(self) -> None:
        assert _revision_kind("   ") is None


class RunningVersionDist(FakeDist):
    """A distribution whose version metadata cannot be read."""

    @property
    def version(self) -> str:
        raise OSError("metadata unreadable")

    @version.setter
    def version(self, value: str) -> None:
        self._ignored_version = value


class TestDistributionEdgeCases:
    def test_falls_back_to_primary_command_name(self) -> None:
        dist = FakeDist()
        with (
            patch(
                "usecli.shared.upgrades.discovery._find_distribution_for_console_script",
                side_effect=[None, dist],
            ),
            patch(
                "usecli.cli.core.ui.title.get_script_command_name",
                return_value="mycli",
            ),
        ):
            install = discover(config=FakeConfig())
        assert install.package == "magic-cli"

    def test_unreadable_metadata_files_are_ignored(self) -> None:
        class RaisingFilesDist(FakeDist):
            def read_text(self, name: str) -> str:
                raise OSError("unreadable")

        install = _install_dist(RaisingFilesDist())
        assert install.source == "index"
        assert install.installer is None

    def test_non_string_metadata_values_are_ignored(self) -> None:
        dist = FakeDist(files={"INSTALLER": 123})
        install = _install_dist(dist)
        assert install.installer is None

    def test_missing_metadata_returns_empty_name(self) -> None:
        dist = FakeDist()
        dist.metadata = None
        install = _install_dist(dist)
        assert install.package == ""

    def test_broken_metadata_returns_empty_name(self) -> None:
        dist = FakeDist()
        dist.metadata = object()
        install = _install_dist(dist)
        assert install.package == ""

    def test_unreadable_version_falls_back_to_config(self) -> None:
        install = _install_dist(RunningVersionDist())
        assert install.version == "9.9.9"


_DEFAULT_CONFIG_SENTINEL = FakeConfig()


def _install_dist(
    dist: FakeDist | None, config: Any = _DEFAULT_CONFIG_SENTINEL
) -> InstallInfo:
    if config is _DEFAULT_CONFIG_SENTINEL:
        config = FakeConfig()
    with (
        patch(
            "usecli.shared.upgrades.discovery._find_distribution_for_console_script",
            return_value=dist,
        ),
        patch(
            "usecli.cli.core.ui.title.get_script_command_name",
            return_value=None,
        ),
    ):
        return discover(config=config)


class TestVersionFallback:
    def test_uses_global_config_when_none_given(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        reset_config()
        try:
            install = _install_dist(None, config=None)
        finally:
            reset_config()
        assert install.version == version("usecli")

    def test_survives_get_config_failure(self) -> None:
        with (
            patch(
                "usecli.shared.config.manager.get_config",
                side_effect=OSError("no config"),
            ),
        ):
            install = _install_dist(None, config=None)
        assert install.version == version("usecli")

    def test_survives_config_version_failure(self) -> None:
        class BrokenConfig:
            def get_project_version(self) -> str:
                raise ValueError("broken toml")

        install = _install_dist(RunningVersionDist(), config=BrokenConfig())
        assert install.version == version("usecli")

    def test_returns_zero_when_everything_fails(self) -> None:
        class BrokenConfig:
            def get_project_version(self) -> str:
                raise ValueError("broken toml")

        with patch("importlib.metadata.version", side_effect=OSError("no metadata")):
            install = _install_dist(RunningVersionDist(), config=BrokenConfig())
        assert install.version == "0.0.0"
