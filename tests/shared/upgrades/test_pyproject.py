"""Tests for persisting upgrades into project dependency metadata."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import Mock, patch

import pytest

from usecli.shared.upgrades.discovery import InstallInfo
from usecli.shared.upgrades.pyproject import (
    PyprojectUpdate,
    _dependency_git_spec,
    _persist_requirements,
    _pinned_revision,
    _project_dir,
    _reinstalled_commit,
    _reinstalled_version,
    persist_upgrade,
    update_project_version,
)


def _install(**overrides: Any) -> InstallInfo:
    defaults: dict[str, Any] = {
        "package": "cli-upgrade",
        "version": "0.1.0",
        "source": "git",
        "installer": "uv",
    }
    defaults.update(overrides)
    return InstallInfo(**defaults)


def _make_project(tmp_path: Any, pyproject: str, venv_name: str = ".venv") -> Any:
    project = tmp_path / "proj"
    (project / venv_name).mkdir(parents=True)
    (project / "pyproject.toml").write_text(pyproject)
    return project


@pytest.fixture
def in_project_venv(tmp_path: Any, monkeypatch: pytest.MonkeyPatch):
    def _enter(project: Any) -> None:
        monkeypatch.setattr(sys, "prefix", str(project / ".venv"))

    return _enter


class TestProjectDir:
    def test_venv_layout_is_matched(self, tmp_path: Any, in_project_venv) -> None:
        project = _make_project(tmp_path, "[project]\n")
        in_project_venv(project)
        assert _project_dir() == project

    def test_non_venv_prefix_never_matches(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _make_project(tmp_path, "[project]\n")
        monkeypatch.setattr(sys, "prefix", str(tmp_path / "proj" / "venvx"))
        assert _project_dir() is None


class TestPersistGlobalInstalls:
    def test_global_prefix_touches_nothing(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        global_dir = tmp_path / "global"
        global_dir.mkdir()
        pyproject = global_dir / "pyproject.toml"
        pyproject.write_text('[project]\nname = "cli-upgrade"\nversion = "0.1.0"\n')
        requirements = global_dir / "requirements.txt"
        requirements.write_text("cli-upgrade @ git+https://github.com/foo/magic.git\n")
        monkeypatch.setattr(sys, "prefix", str(global_dir))

        outcome = persist_upgrade(_install())

        assert outcome.updated is False
        assert outcome.reason == "not a project-managed environment"
        assert 'version = "0.1.0"' in pyproject.read_text()
        assert "git+https://github.com/foo/magic.git" in requirements.read_text()


class TestUpdateProjectVersion:
    def test_rewrites_version_preserving_formatting(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "magic-cli"\nversion = "0.1.0"  # pinned\n'
            '\n[project.scripts]\nupp = "cli_upgrade:main"\n'
        )
        changed, previous = update_project_version(pyproject, "0.1.1")
        assert changed is True
        assert previous == "0.1.0"
        content = pyproject.read_text()
        assert 'version = "0.1.1"  # pinned' in content
        assert 'name = "magic-cli"' in content
        assert 'upp = "cli_upgrade:main"' in content

    def test_matching_version_is_a_noop(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "0.1.1"\n')
        changed, previous = update_project_version(pyproject, "0.1.1")
        assert changed is False
        assert previous == "0.1.1"
        assert pyproject.read_text() == '[project]\nversion = "0.1.1"\n'

    def test_missing_version_reports_nothing(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "magic-cli"\n')
        changed, previous = update_project_version(pyproject, "0.1.1")
        assert changed is False
        assert previous is None

    def test_version_outside_project_table_is_ignored(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.usecli]\nversion = "9.9.9"\n\n[project]\n')
        changed, previous = update_project_version(pyproject, "0.1.1")
        assert changed is False
        assert previous is None
        assert 'version = "9.9.9"' in pyproject.read_text()

    def test_missing_trailing_newline_is_preserved(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "0.1.0"')
        changed, _ = update_project_version(pyproject, "0.1.1")
        assert changed is True
        assert pyproject.read_text() == '[project]\nversion = "0.1.1"'

    def test_unreadable_file_is_a_noop(self, tmp_path: Any) -> None:
        changed, previous = update_project_version(tmp_path, "0.1.1")
        assert changed is False
        assert previous is None

    def test_unwritable_file_is_a_noop(self, tmp_path: Any) -> None:
        import os

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "0.1.0"\n')
        os.chmod(pyproject, 0o444)
        try:
            changed, previous = update_project_version(pyproject, "0.1.1")
        finally:
            os.chmod(pyproject, 0o644)
        assert changed is False
        assert previous == "0.1.0"

    def test_unreadable_dependency_scan_is_empty(self, tmp_path: Any) -> None:
        assert _dependency_git_spec(tmp_path, "cli-upgrade") is None


class TestDependencyGitSpec:
    def test_finds_git_dependency_line(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\ndependencies = [\n"
            '    "usecli>=0.1.0",\n'
            '    "cli-upgrade @ git+https://github.com/foo/magic.git",\n'
            "]\n"
        )
        spec = _dependency_git_spec(pyproject, "cli-upgrade")
        assert spec is not None
        assert "git+https://github.com/foo/magic.git" in spec

    def test_package_without_git_dependency_is_not_found(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\ndependencies = ["cli-upgrade>=0.1.0"]\n')
        assert _dependency_git_spec(pyproject, "cli-upgrade") is None

    def test_unknown_package_is_not_found(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\ndependencies = []\n")
        assert _dependency_git_spec(pyproject, "cli-upgrade") is None

    def test_non_list_dependencies_returns_none(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\ndependencies = "not-a-list"\n')
        assert _dependency_git_spec(pyproject, "cli-upgrade") is None

    def test_spec_without_parseable_name_is_skipped(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            "[project]\ndependencies = [\n"
            '    "!!! @ git+https://github.com/foo/magic.git",\n'
            '    "cli-upgrade @ git+https://github.com/foo/magic.git",\n'
            "]\n"
        )
        spec = _dependency_git_spec(pyproject, "cli-upgrade")
        assert spec is not None
        assert "cli-upgrade @ git+" in spec


class TestPinnedRevision:
    @pytest.mark.parametrize(
        ("spec_line", "expected"),
        [
            ('"cli-upgrade @ git+https://github.com/foo/magic.git",', None),
            ('"cli-upgrade @ git+https://github.com/foo/magic.git@main",', "main"),
            ('"cli-upgrade @ git+https://github.com/foo/magic.git@v1.2.3",', "v1.2.3"),
            (
                '"cli-upgrade @ git+https://github.com/foo/magic.git@'
                + "a" * 40
                + '",',
                "a" * 40,
            ),
            ('cli-upgrade = { git = "https://github.com/foo/magic.git" }', None),
            (
                'cli-upgrade = { git = "https://github.com/foo/magic.git", rev = "v2" }',
                "v2",
            ),
        ],
    )
    def test_extraction(self, spec_line: str, expected: str | None) -> None:
        assert _pinned_revision(spec_line) == expected


class TestReinstalledVersion:
    def test_reads_version_from_distribution(self) -> None:
        dist = Mock(version="0.1.2")
        with patch(
            "usecli.shared.upgrades.pyproject._refind_running_distribution",
            return_value=dist,
        ):
            assert _reinstalled_version() == "0.1.2"

    def test_missing_distribution_returns_none(self) -> None:
        with patch(
            "usecli.shared.upgrades.pyproject._refind_running_distribution",
            return_value=None,
        ):
            assert _reinstalled_version() is None

    def test_unreadable_version_returns_none(self) -> None:
        dist = Mock(spec=["version"])

        def _raise() -> str:
            raise OSError("unreadable")

        type(dist).version = property(lambda self: _raise())
        with patch(
            "usecli.shared.upgrades.pyproject._refind_running_distribution",
            return_value=dist,
        ):
            assert _reinstalled_version() is None

    def test_refind_resets_the_distribution_cache(self) -> None:
        dist = Mock(version="0.1.2")
        with (
            patch("usecli.shared.config.manager._reset_distributions_cache") as reset,
            patch(
                "usecli.shared.upgrades.discovery._find_running_distribution",
                return_value=dist,
            ) as find,
        ):
            from usecli.shared.upgrades.pyproject import _refind_running_distribution

            assert _refind_running_distribution() is dist
        reset.assert_called_once()
        find.assert_called_once()


class TestGetTomllib:
    def test_falls_back_to_tomli_on_python_3_10(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import types

        from usecli.shared.upgrades import pyproject

        fake_tomli = types.ModuleType("tomli")
        monkeypatch.setitem(sys.modules, "tomli", fake_tomli)
        monkeypatch.setattr(pyproject.sys, "version_info", (3, 10))
        assert pyproject._get_tomllib() is fake_tomli


class TestReadProjectNameEdgeCases:
    def test_corrupt_toml_returns_none(self, tmp_path: Any, in_project_venv) -> None:
        project = _make_project(tmp_path, "[project]\nname = ")
        in_project_venv(project)
        outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.reason == "package is not a dependency of this project"

    def test_missing_project_name_falls_through_to_dependency_path(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = _make_project(tmp_path, "[project]\ndependencies = []\n")
        in_project_venv(project)
        outcome = persist_upgrade(_install())
        assert outcome.reason == "package is not a dependency of this project"


class TestPersistUpgradeDispatch:
    def test_non_project_environment_is_skipped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "prefix", "/usr")
        outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.path is None
        assert outcome.reason == "not a project-managed environment"

    def test_venv_without_metadata_reports_unmanaged(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = tmp_path / "proj"
        (project / ".venv").mkdir(parents=True)
        monkeypatch.setattr(sys, "prefix", str(project / ".venv"))
        outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.path is None
        assert outcome.reason == "package is not a dependency of this project"

    def test_self_package_version_is_persisted(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = _make_project(
            tmp_path, '[project]\nname = "magic-cli"\nversion = "0.1.0"\n'
        )
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_version",
            return_value="0.1.1",
        ):
            outcome = persist_upgrade(_install(package="magic-cli"))
        assert outcome.updated is True
        assert outcome.previous_version == "0.1.0"
        assert outcome.new_version == "0.1.1"
        assert outcome.summary is not None
        assert "pyproject.toml" in outcome.summary
        assert 'version = "0.1.1"' in (project / "pyproject.toml").read_text()

    def test_self_package_without_version_reports_reason(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = _make_project(tmp_path, '[project]\nname = "magic-cli"\n')
        in_project_venv(project)
        with (
            patch(
                "usecli.shared.upgrades.pyproject._reinstalled_version",
                return_value="0.1.1",
            ),
        ):
            outcome = persist_upgrade(_install(package="magic-cli"))
        assert outcome.updated is False
        assert outcome.reason == "no static version in [project]"

    def test_self_package_with_undeterminable_version(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = _make_project(
            tmp_path, '[project]\nname = "magic-cli"\nversion = "0.1.0"\n'
        )
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_version",
            return_value=None,
        ):
            outcome = persist_upgrade(_install(package="magic-cli"))
        assert outcome.updated is False
        assert outcome.reason == "upgraded version could not be determined"

    def test_self_package_with_matching_version_is_a_noop(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = _make_project(
            tmp_path, '[project]\nname = "magic-cli"\nversion = "0.1.1"\n'
        )
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_version",
            return_value="0.1.1",
        ):
            outcome = persist_upgrade(_install(package="magic-cli"))
        assert outcome.updated is False
        assert outcome.reason == "version already matches"
        assert outcome.summary is None

    def test_git_dependency_lock_is_refreshed(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = _make_project(
            tmp_path,
            '[project]\nname = "consumer"\ndependencies = [\n'
            '    "cli-upgrade @ git+https://github.com/foo/magic.git",\n]\n',
        )
        in_project_venv(project)
        with (
            patch("shutil.which", return_value="/usr/local/bin/uv"),
            patch(
                "subprocess.run", return_value=Mock(returncode=0, stdout="", stderr="")
            ) as run,
            patch(
                "usecli.shared.upgrades.pyproject._reinstalled_version",
                return_value="0.1.2",
            ),
        ):
            outcome = persist_upgrade(_install())
        assert outcome.updated is True
        assert outcome.new_version == "0.1.2"
        assert outcome.summary is not None
        assert "uv.lock" in outcome.summary
        assert run.call_args.args[0] == [
            "/usr/local/bin/uv",
            "lock",
            "--upgrade-package",
            "cli-upgrade",
        ]
        assert run.call_args.kwargs["cwd"] == project

    def test_statically_pinned_dependency_is_skipped(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = _make_project(
            tmp_path,
            '[project]\nname = "consumer"\ndependencies = [\n'
            '    "cli-upgrade @ git+https://github.com/foo/magic.git@'
            + "a" * 40
            + '",\n]\n',
        )
        in_project_venv(project)
        with patch("subprocess.run") as run:
            outcome = persist_upgrade(_install())
        run.assert_not_called()
        assert outcome.updated is False
        assert outcome.reason is not None
        assert "pins revision" in outcome.reason

    def test_package_not_declared_as_dependency_is_skipped(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = _make_project(
            tmp_path, '[project]\nname = "consumer"\ndependencies = []\n'
        )
        in_project_venv(project)
        outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.reason == "package is not a dependency of this project"

    def test_missing_uv_reports_reason(self, tmp_path: Any, in_project_venv) -> None:
        project = _make_project(
            tmp_path,
            '[project]\nname = "consumer"\ndependencies = [\n'
            '    "cli-upgrade @ git+https://github.com/foo/magic.git",\n]\n',
        )
        in_project_venv(project)
        with patch("shutil.which", return_value=None):
            outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.reason is not None
        assert "uv is required" in outcome.reason

    def test_failed_uv_lock_reports_reason(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = _make_project(
            tmp_path,
            '[project]\nname = "consumer"\ndependencies = [\n'
            '    "cli-upgrade @ git+https://github.com/foo/magic.git",\n]\n',
        )
        in_project_venv(project)
        with (
            patch("shutil.which", return_value="/usr/local/bin/uv"),
            patch(
                "subprocess.run",
                return_value=Mock(returncode=2, stdout="", stderr="resolve failed"),
            ),
        ):
            outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.reason is not None
        assert "uv lock failed" in outcome.reason
        assert "resolve failed" in outcome.reason

    def test_uv_lock_subprocess_error_reports_reason(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        import subprocess

        project = _make_project(
            tmp_path,
            '[project]\nname = "consumer"\ndependencies = [\n'
            '    "cli-upgrade @ git+https://github.com/foo/magic.git",\n]\n',
        )
        in_project_venv(project)
        with (
            patch("shutil.which", return_value="/usr/local/bin/uv"),
            patch(
                "subprocess.run",
                side_effect=subprocess.SubprocessError("timeout"),
            ),
        ):
            outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.reason is not None
        assert "uv lock failed" in outcome.reason


def test_pyproject_update_defaults() -> None:
    outcome = PyprojectUpdate()
    assert outcome.updated is False
    assert outcome.path is None


class TestReinstalledCommit:
    def test_reads_commit_from_direct_url(self) -> None:
        commit = "b" * 40
        payload = '{"vcs_info": {"vcs": "git", "commit_id": "' + commit + '"}}'
        dist = Mock(
            read_text=lambda name: payload if name == "direct_url.json" else None
        )
        with patch(
            "usecli.shared.upgrades.pyproject._refind_running_distribution",
            return_value=dist,
        ):
            assert _reinstalled_commit() == commit

    def test_missing_distribution_returns_none(self) -> None:
        with patch(
            "usecli.shared.upgrades.pyproject._refind_running_distribution",
            return_value=None,
        ):
            assert _reinstalled_commit() is None

    def test_unreadable_metadata_returns_none(self) -> None:
        dist = Mock(read_text=Mock(side_effect=OSError("boom")))
        with patch(
            "usecli.shared.upgrades.pyproject._refind_running_distribution",
            return_value=dist,
        ):
            assert _reinstalled_commit() is None

    def test_malformed_metadata_returns_none(self) -> None:
        dist = Mock(read_text=lambda name: "{not json")
        with patch(
            "usecli.shared.upgrades.pyproject._refind_running_distribution",
            return_value=dist,
        ):
            assert _reinstalled_commit() is None

    def test_non_vcs_metadata_returns_none(self) -> None:
        dist = Mock(read_text=lambda name: '{"url": "https://example.com/x.whl"}')
        with patch(
            "usecli.shared.upgrades.pyproject._refind_running_distribution",
            return_value=dist,
        ):
            assert _reinstalled_commit() is None


class TestPersistRequirements:
    def _requirements_project(self, tmp_path: Any, requirements: str) -> Any:
        project = tmp_path / "proj"
        (project / ".venv").mkdir(parents=True)
        (project / "requirements.txt").write_text(requirements)
        return project

    def test_git_revision_rewritten_to_installed_commit(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = self._requirements_project(
            tmp_path,
            "rich>=15.0\ncli-upgrade @ git+https://github.com/foo/magic.git@main\n",
        )
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_commit",
            return_value="b" * 40,
        ):
            outcome = persist_upgrade(_install())
        assert outcome.updated is True
        assert outcome.previous_version == "main"
        assert outcome.new_version == "b" * 40
        assert outcome.summary is not None
        assert "requirements.txt" in outcome.summary
        content = (project / "requirements.txt").read_text()
        assert (
            f"cli-upgrade @ git+https://github.com/foo/magic.git@{'b' * 40}" in content
        )
        assert "rich>=15.0" in content

    def test_unpinned_git_requirement_gets_pinned(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = self._requirements_project(
            tmp_path, "cli-upgrade @ git+https://github.com/foo/magic.git\n"
        )
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_commit",
            return_value="b" * 40,
        ):
            outcome = persist_upgrade(_install())
        assert outcome.updated is True
        assert outcome.previous_version is None
        content = (project / "requirements.txt").read_text()
        assert (
            f"cli-upgrade @ git+https://github.com/foo/magic.git@{'b' * 40}" in content
        )

    def test_legacy_egg_form_is_rewritten(self, tmp_path: Any, in_project_venv) -> None:
        project = self._requirements_project(
            tmp_path, "git+https://github.com/foo/magic.git@v1.0#egg=cli_upgrade\n"
        )
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_commit",
            return_value="b" * 40,
        ):
            outcome = persist_upgrade(_install(package="cli-upgrade"))
        assert outcome.updated is True
        assert outcome.previous_version == "v1.0"
        content = (project / "requirements.txt").read_text()
        assert (
            f"git+https://github.com/foo/magic.git@{'b' * 40}#egg=cli_upgrade"
            in content
        )

    def test_ssh_urls_are_not_confused_by_user_at_host(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = self._requirements_project(
            tmp_path, "cli-upgrade @ git+ssh://git@github.com/foo/magic.git@main\n"
        )
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_commit",
            return_value="b" * 40,
        ):
            outcome = persist_upgrade(_install())
        assert outcome.previous_version == "main"
        content = (project / "requirements.txt").read_text()
        assert "git+ssh://git@github.com/foo/magic.git@main" not in content
        assert f"magic.git@{'b' * 40}" in content

    def test_index_pin_updated_to_installed_version(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = self._requirements_project(tmp_path, "cli-upgrade==0.1.0\n")
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_version",
            return_value="0.1.2",
        ):
            outcome = persist_upgrade(_install(package="cli-upgrade", source="index"))
        assert outcome.updated is True
        assert outcome.previous_version == "0.1.0"
        assert outcome.new_version == "0.1.2"
        assert "cli-upgrade==0.1.2" in (project / "requirements.txt").read_text()

    def test_matching_index_pin_is_a_noop(self, tmp_path: Any, in_project_venv) -> None:
        project = self._requirements_project(tmp_path, "cli-upgrade==0.1.2\n")
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_version",
            return_value="0.1.2",
        ):
            outcome = persist_upgrade(_install(package="cli-upgrade", source="index"))
        assert outcome.updated is False
        assert outcome.reason == "version already matches"

    def test_unpinned_requirement_is_skipped(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = self._requirements_project(tmp_path, "cli-upgrade\n")
        in_project_venv(project)
        outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.reason == "package not found in requirements.txt"

    def test_floating_requirement_is_skipped(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = self._requirements_project(tmp_path, "cli-upgrade>=0.1.0\n")
        in_project_venv(project)
        outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.reason == "package not found in requirements.txt"

    def test_direct_url_requirement_is_skipped(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = self._requirements_project(
            tmp_path, "cli-upgrade @ https://example.com/wheels/cli_upgrade-0.1.0.whl\n"
        )
        in_project_venv(project)
        outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.reason is not None
        assert "direct URL" in outcome.reason

    def test_missing_commit_reports_reason(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = self._requirements_project(
            tmp_path, "cli-upgrade @ git+https://github.com/foo/magic.git@main\n"
        )
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_commit",
            return_value=None,
        ):
            outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.reason == "upgraded commit could not be determined"

    def test_missing_version_reports_reason(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = self._requirements_project(tmp_path, "cli-upgrade==0.1.0\n")
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_version",
            return_value=None,
        ):
            outcome = persist_upgrade(_install(package="cli-upgrade", source="index"))
        assert outcome.updated is False
        assert outcome.reason == "upgraded version could not be determined"

    def test_package_absent_reports_reason(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = self._requirements_project(
            tmp_path, "rich>=15.0\n# cli-upgrade @ git+x\n"
        )
        in_project_venv(project)
        outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.reason == "package not found in requirements.txt"

    def test_requirements_used_when_pyproject_does_not_manage(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = tmp_path / "proj"
        (project / ".venv").mkdir(parents=True)
        (project / "pyproject.toml").write_text(
            '[project]\nname = "something-else"\ndependencies = []\n'
        )
        (project / "requirements.txt").write_text(
            "cli-upgrade @ git+https://github.com/foo/magic.git@main\n"
        )
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_commit",
            return_value="b" * 40,
        ):
            outcome = persist_upgrade(_install())
        assert outcome.updated is True
        assert outcome.path == str(project / "requirements.txt")

    def test_uv_lock_takes_precedence_over_requirements(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = _make_project(
            tmp_path,
            '[project]\nname = "consumer"\ndependencies = [\n'
            '    "cli-upgrade @ git+https://github.com/foo/magic.git",\n]\n',
        )
        (project / "requirements.txt").write_text(
            "cli-upgrade @ git+https://github.com/foo/magic.git@main\n"
        )
        in_project_venv(project)
        with (
            patch("shutil.which", return_value="/usr/local/bin/uv"),
            patch(
                "subprocess.run", return_value=Mock(returncode=0, stdout="", stderr="")
            ),
        ):
            outcome = persist_upgrade(_install())
        assert outcome.updated is True
        assert "uv.lock" in (outcome.summary or "")
        assert (
            "git+https://github.com/foo/magic.git@main"
            in (project / "requirements.txt").read_text()
        )

    def test_unwritable_requirements_reports_reason(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        import os

        project = self._requirements_project(
            tmp_path, "cli-upgrade @ git+https://github.com/foo/magic.git@main\n"
        )
        in_project_venv(project)
        os.chmod(project / "requirements.txt", 0o444)
        try:
            with patch(
                "usecli.shared.upgrades.pyproject._reinstalled_commit",
                return_value="b" * 40,
            ):
                outcome = persist_upgrade(_install())
        finally:
            os.chmod(project / "requirements.txt", 0o644)
        assert outcome.updated is False
        assert outcome.reason == "could not write requirements.txt"


class TestRemainingEdgeCases:
    def test_ghost_project_dir_is_skipped(
        self, tmp_path: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "prefix", str(tmp_path / "ghost" / ".venv"))
        outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.reason == "not a project-managed environment"

    def test_empty_direct_url_returns_none(self) -> None:
        dist = Mock(read_text=Mock(return_value=None))
        with patch(
            "usecli.shared.upgrades.pyproject._refind_running_distribution",
            return_value=dist,
        ):
            assert _reinstalled_commit() is None

    def test_non_dict_direct_url_returns_none(self) -> None:
        dist = Mock(
            read_text=lambda name: "[1, 2]" if name == "direct_url.json" else None
        )
        with patch(
            "usecli.shared.upgrades.pyproject._refind_running_distribution",
            return_value=dist,
        ):
            assert _reinstalled_commit() is None

    def test_vcs_info_without_commit_returns_none(self) -> None:
        dist = Mock(
            read_text=lambda name: (
                '{"vcs_info": {}}' if name == "direct_url.json" else None
            )
        )
        with patch(
            "usecli.shared.upgrades.pyproject._refind_running_distribution",
            return_value=dist,
        ):
            assert _reinstalled_commit() is None

    def test_other_package_git_lines_are_ignored(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = tmp_path / "proj"
        (project / ".venv").mkdir(parents=True)
        (project / "requirements.txt").write_text(
            "other-pkg @ git+https://github.com/foo/other.git@dev\n"
            "cli-upgrade @ git+https://github.com/foo/magic.git@main\n"
        )
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_commit",
            return_value="b" * 40,
        ):
            outcome = persist_upgrade(_install())
        assert outcome.updated is True
        assert outcome.previous_version == "main"
        content = (project / "requirements.txt").read_text()
        assert "other-pkg @ git+https://github.com/foo/other.git@dev" in content

    def test_unpinned_git_line_with_comment_pins_before_comment(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = tmp_path / "proj"
        (project / ".venv").mkdir(parents=True)
        (project / "requirements.txt").write_text(
            "cli-upgrade @ git+https://github.com/foo/magic.git  # installed via CI\n"
        )
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_commit",
            return_value="b" * 40,
        ):
            outcome = persist_upgrade(_install())
        assert outcome.updated is True
        content = (project / "requirements.txt").read_text()
        assert f"magic.git@{'b' * 40}  # installed via CI" in content

    def test_unreadable_requirements_file_reports_reason(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = tmp_path / "proj"
        (project / ".venv").mkdir(parents=True)
        (project / "requirements.txt").write_text("cli-upgrade==0.1.0\n")
        in_project_venv(project)
        outcome = _persist_requirements(project, _install())
        assert outcome.updated is False
        assert outcome.reason == "could not read requirements.txt"

    def test_git_pin_already_matching_commit_is_a_noop(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        commit = "b" * 40
        project = tmp_path / "proj"
        (project / ".venv").mkdir(parents=True)
        (project / "requirements.txt").write_text(
            f"cli-upgrade @ git+https://github.com/foo/magic.git@{commit}\n"
        )
        in_project_venv(project)
        with patch(
            "usecli.shared.upgrades.pyproject._reinstalled_commit",
            return_value=commit,
        ):
            outcome = persist_upgrade(_install())
        assert outcome.updated is False
        assert outcome.reason == "pin already matches"
        assert outcome.previous_version == commit


class TestUvSourcesDeclaration:
    def test_sources_git_entry_is_recognized(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "consumer"\ndependencies = ["cli-upgrade"]\n'
            "\n[tool.uv.sources]\n"
            'cli-upgrade = { git = "https://github.com/foo/magic.git" }\n'
        )
        spec = _dependency_git_spec(pyproject, "cli-upgrade")
        assert spec is not None
        assert "git+https://github.com/foo/magic.git" in spec
        assert "@" not in spec.replace("cli-upgrade @ ", "", 1)

    def test_sources_branch_entry_is_movable(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "consumer"\ndependencies = ["cli-upgrade"]\n'
            "\n[tool.uv.sources]\n"
            'cli-upgrade = { git = "https://github.com/foo/magic.git", branch = "main" }\n'
        )
        spec = _dependency_git_spec(pyproject, "cli-upgrade")
        assert spec is not None
        assert spec.endswith("@main")
        assert _pinned_revision(spec) == "main"

    def test_sources_tag_entry_is_a_static_pin(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "consumer"\ndependencies = ["cli-upgrade"]\n'
            "\n[tool.uv.sources]\n"
            'cli-upgrade = { git = "https://github.com/foo/magic.git", tag = "v0.1.0" }\n'
        )
        spec = _dependency_git_spec(pyproject, "cli-upgrade")
        assert spec is not None
        assert _pinned_revision(spec) == "v0.1.0"

    def test_non_git_sources_entry_is_ignored(self, tmp_path: Any) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text(
            '[project]\nname = "consumer"\ndependencies = ["cli-upgrade"]\n'
            "\n[tool.uv.sources]\n"
            'cli-upgrade = { path = "../cli-upgrade" }\n'
        )
        assert _dependency_git_spec(pyproject, "cli-upgrade") is None

    def test_sources_dispatch_refreshes_the_lock(
        self, tmp_path: Any, in_project_venv
    ) -> None:
        project = tmp_path / "proj"
        (project / ".venv").mkdir(parents=True)
        (project / "pyproject.toml").write_text(
            '[project]\nname = "consumer"\ndependencies = ["cli-upgrade"]\n'
            "\n[tool.uv.sources]\n"
            'cli-upgrade = { git = "https://github.com/foo/magic.git" }\n'
        )
        in_project_venv(project)
        with (
            patch("shutil.which", return_value="/usr/local/bin/uv"),
            patch(
                "subprocess.run", return_value=Mock(returncode=0, stdout="", stderr="")
            ) as run,
            patch(
                "usecli.shared.upgrades.pyproject._reinstalled_version",
                return_value="0.1.4",
            ),
        ):
            outcome = persist_upgrade(_install())
        assert outcome.updated is True
        assert run.call_args.args[0] == [
            "/usr/local/bin/uv",
            "lock",
            "--upgrade-package",
            "cli-upgrade",
        ]
