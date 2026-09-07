"""Tests for upgrade installer strategies."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import Mock, patch

import pytest

from usecli.shared.upgrades.discovery import InstallInfo
from usecli.shared.upgrades.installer import (
    _is_uv_tool_environment,
    _pip_target,
    _shutil_which,
    upgrade,
)
from usecli.shared.upgrades.pyproject import PyprojectUpdate


def _install(**overrides: Any) -> InstallInfo:
    defaults: dict[str, Any] = {
        "package": "magic-cli",
        "version": "1.4.2",
        "source": "index",
        "installer": "uv",
    }
    defaults.update(overrides)
    return InstallInfo(**defaults)


def _mock_run(returncode: int = 0, stderr: str = "") -> Mock:
    return Mock(returncode=returncode, stdout="", stderr=stderr)


class TestPipTarget:
    def test_index_target_is_package_name(self) -> None:
        assert _pip_target(_install()) == "magic-cli"

    def test_git_target_includes_url_and_revision(self) -> None:
        install = _install(
            source="git",
            url="https://github.com/foo/magic.git",
            revision="main",
        )
        assert (
            _pip_target(install)
            == "magic-cli @ git+https://github.com/foo/magic.git@main"
        )

    def test_git_target_without_revision(self) -> None:
        install = _install(source="git", url="https://github.com/foo/magic.git")
        assert (
            _pip_target(install) == "magic-cli @ git+https://github.com/foo/magic.git"
        )


class TestUvToolEnvironmentDetection:
    def test_uv_tools_path_is_detected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            sys,
            "executable",
            "/home/dev/.local/share/uv/tools/magic-cli/bin/python",
        )
        assert _is_uv_tool_environment() is True

    def test_venv_path_is_not_uv_tools(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            sys,
            "executable",
            "/home/dev/projects/magic/.venv/bin/python",
        )
        assert _is_uv_tool_environment() is False


class TestBlockedUpgrades:
    def test_frozen_bundle_is_never_mutated(self) -> None:
        result = upgrade(_install(frozen=True, pinned=True))
        assert result.success is False
        assert result.command is None
        assert "frozen bundle" in (result.message or "")

    def test_editable_install_is_never_mutated(self) -> None:
        result = upgrade(_install(source="editable", pinned=True))
        assert result.success is False
        assert "editable" in (result.message or "")

    def test_pinned_install_is_never_mutated(self) -> None:
        result = upgrade(
            _install(
                source="git",
                revision="d" * 40,
                pinned=True,
                pinned_reason=f"Git commit ({'d' * 40})",
            )
        )
        assert result.success is False
        assert "pinned" in (result.message or "")

    def test_unknown_source_is_never_mutated(self) -> None:
        result = upgrade(_install(package="", source="unknown", installer=None))
        assert result.success is False
        assert "Could not determine" in (result.message or "")


class TestUvToolUpgrades:
    def test_index_install_uses_tool_upgrade(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            sys,
            "executable",
            "/home/dev/.local/share/uv/tools/magic-cli/bin/python",
        )
        with (
            patch(
                "usecli.shared.upgrades.installer._shutil_which",
                return_value="/usr/local/bin/uv",
            ),
            patch("subprocess.run", return_value=_mock_run()) as run,
        ):
            result = upgrade(_install())
        assert result.success is True
        assert run.call_count == 1
        assert run.call_args.args[0] == [
            "/usr/local/bin/uv",
            "tool",
            "upgrade",
            "magic-cli",
        ]

    def test_git_install_reinstalls_from_source(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            sys,
            "executable",
            "/home/dev/.local/share/uv/tools/magic-cli/bin/python",
        )
        install = _install(
            source="git",
            url="https://github.com/foo/magic.git",
            revision="main",
        )
        with (
            patch(
                "usecli.shared.upgrades.installer._shutil_which",
                return_value="/usr/local/bin/uv",
            ),
            patch("subprocess.run", return_value=_mock_run()) as run,
        ):
            result = upgrade(install)
        assert result.success is True
        assert run.call_args.args[0] == [
            "/usr/local/bin/uv",
            "tool",
            "install",
            "--force",
            "magic-cli @ git+https://github.com/foo/magic.git@main",
        ]

    def test_missing_uv_in_tool_env_fails_without_running(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            sys,
            "executable",
            "/home/dev/.local/share/uv/tools/magic-cli/bin/python",
        )
        with (
            patch(
                "usecli.shared.upgrades.installer._shutil_which",
                return_value=None,
            ),
            patch("subprocess.run") as run,
        ):
            result = upgrade(_install())
        assert result.success is False
        run.assert_not_called()
        assert "uv is required" in (result.message or "")


class TestUvPipUpgrades:
    def test_non_tool_uv_install_targets_current_interpreter(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            sys,
            "executable",
            "/home/dev/projects/magic/.venv/bin/python",
        )
        with (
            patch(
                "usecli.shared.upgrades.installer._shutil_which",
                return_value="/usr/local/bin/uv",
            ),
            patch("subprocess.run", return_value=_mock_run()) as run,
        ):
            result = upgrade(_install())
        assert result.success is True
        assert run.call_args.args[0] == [
            "/usr/local/bin/uv",
            "pip",
            "install",
            "--python",
            sys.executable,
            "--upgrade",
            "magic-cli",
        ]


class TestPipxUpgrades:
    def test_pipx_install_uses_pipx_upgrade(self) -> None:
        install = _install(installer="pipx")
        with (
            patch(
                "usecli.shared.upgrades.installer._shutil_which",
                return_value="/usr/local/bin/pipx",
            ),
            patch("subprocess.run", return_value=_mock_run()) as run,
        ):
            result = upgrade(install)
        assert result.success is True
        assert run.call_args.args[0] == [
            "/usr/local/bin/pipx",
            "upgrade",
            "magic-cli",
        ]

    def test_missing_pipx_reports_manual_command(self) -> None:
        install = _install(installer="pipx")
        with patch(
            "usecli.shared.upgrades.installer._shutil_which",
            return_value=None,
        ):
            result = upgrade(install)
        assert result.success is False
        assert "pipx upgrade magic-cli" in (result.message or "")


class TestPipFallback:
    def test_pip_install_targets_current_interpreter(self) -> None:
        install = _install(installer="pip")
        with patch("subprocess.run", return_value=_mock_run()) as run:
            result = upgrade(install)
        assert result.success is True
        assert run.call_args.args[0] == [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "magic-cli",
        ]

    def test_failed_upgrade_includes_manual_command(self) -> None:
        install = _install(installer="pip")
        with patch(
            "subprocess.run",
            return_value=_mock_run(returncode=1, stderr="boom"),
        ):
            result = upgrade(install)
        assert result.success is False
        assert result.message is not None
        assert "exit code 1" in result.message
        assert "boom" in result.message
        assert "Run manually:" in result.message

    def test_missing_pip_binary_is_reported(self) -> None:
        install = _install(installer="pip")
        with patch("subprocess.run", side_effect=OSError("no pip")):
            result = upgrade(install)
        assert result.success is False
        assert "Failed to run" in (result.message or "")


class TestRunHelpers:
    def test_shutil_which_wrapper_resolves_binaries(self) -> None:
        assert _shutil_which(sys.executable) == sys.executable
        assert _shutil_which("definitely-not-a-real-command-xyz") is None

    def test_long_failure_output_is_truncated(self) -> None:
        install = _install(installer="pip")
        with patch(
            "subprocess.run",
            return_value=Mock(returncode=1, stderr="x" * 500),
        ):
            result = upgrade(install)
        assert result.success is False
        assert result.message is not None
        assert "x" * 400 in result.message
        head = "y" * 400
        assert head not in result.message


class TestPyprojectPersistence:
    def test_successful_upgrade_persists_project_metadata(self) -> None:
        install = _install(installer="pip")
        outcome = PyprojectUpdate(
            path="/p/pyproject.toml",
            previous_version="0.1.0",
            new_version="0.1.1",
            updated=True,
        )
        with (
            patch("subprocess.run", return_value=_mock_run()),
            patch(
                "usecli.shared.upgrades.installer.persist_upgrade",
                return_value=outcome,
            ) as persist,
        ):
            result = upgrade(install)
        persist.assert_called_once_with(install, None)
        assert result.pyproject is outcome

    def test_failed_upgrade_skips_persistence(self) -> None:
        install = _install(installer="pip")
        with (
            patch(
                "subprocess.run",
                return_value=_mock_run(returncode=1, stderr="boom"),
            ),
            patch("usecli.shared.upgrades.installer.persist_upgrade") as persist,
        ):
            result = upgrade(install)
        persist.assert_not_called()
        assert result.pyproject is None


class TestTargetRevision:
    def test_git_target_prefers_target_revision(self) -> None:
        install = _install(
            source="git",
            url="https://github.com/foo/magic.git",
            revision="main",
        )
        assert (
            _pip_target(install, target_revision="v0.1.4")
            == "magic-cli @ git+https://github.com/foo/magic.git@v0.1.4"
        )

    def test_git_target_falls_back_to_install_revision(self) -> None:
        install = _install(
            source="git",
            url="https://github.com/foo/magic.git",
            revision="main",
        )
        assert (
            _pip_target(install)
            == "magic-cli @ git+https://github.com/foo/magic.git@main"
        )

    def test_uv_pip_upgrade_installs_the_release_tag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            sys,
            "executable",
            "/home/dev/projects/magic/.venv/bin/python",
        )
        install = _install(
            source="git",
            url="https://github.com/foo/magic.git",
            revision="main",
        )
        with (
            patch(
                "usecli.shared.upgrades.installer._shutil_which",
                return_value="/usr/local/bin/uv",
            ),
            patch("subprocess.run", return_value=_mock_run()) as run,
        ):
            result = upgrade(install, target_revision="v0.1.4")
        assert result.success is True
        assert run.call_args.args[0][-1] == (
            "magic-cli @ git+https://github.com/foo/magic.git@v0.1.4"
        )

    def test_pipx_git_upgrade_installs_the_release_tag(self) -> None:
        install = _install(
            installer="pipx",
            source="git",
            url="https://github.com/foo/magic.git",
            revision="main",
        )
        with (
            patch(
                "usecli.shared.upgrades.installer._shutil_which",
                return_value="/usr/local/bin/pipx",
            ),
            patch("subprocess.run", return_value=_mock_run()) as run,
        ):
            result = upgrade(install, target_revision="v0.1.4")
        assert result.success is True
        assert run.call_args.args[0] == [
            "/usr/local/bin/pipx",
            "install",
            "--force",
            "magic-cli @ git+https://github.com/foo/magic.git@v0.1.4",
        ]

    def test_pipx_index_upgrade_still_uses_upgrade(self) -> None:
        install = _install(installer="pipx")
        with (
            patch(
                "usecli.shared.upgrades.installer._shutil_which",
                return_value="/usr/local/bin/pipx",
            ),
            patch("subprocess.run", return_value=_mock_run()) as run,
        ):
            upgrade(install)
        assert run.call_args.args[0] == [
            "/usr/local/bin/pipx",
            "upgrade",
            "magic-cli",
        ]
