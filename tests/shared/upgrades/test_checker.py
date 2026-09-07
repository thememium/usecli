"""Tests for upgrade checking (PyPI and Git branch comparisons)."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import pytest

from usecli.shared.upgrades.checker import (
    _display_url,
    _fetch_git_head,
    _fetch_pypi_latest,
    _normalize_pypi_name,
    _version_is_newer,
    check,
)
from usecli.shared.upgrades.discovery import InstallInfo


def _install(**overrides: Any) -> InstallInfo:
    defaults: dict[str, Any] = {
        "package": "magic-cli",
        "version": "1.4.2",
        "source": "index",
    }
    defaults.update(overrides)
    return InstallInfo(**defaults)


class TestNormalizePypiName:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("magic-cli", "magic-cli"),
            ("Magic_CLI", "magic-cli"),
            ("my..cli", "my-cli"),
            ("UseCLI", "usecli"),
        ],
    )
    def test_normalization(self, raw: str, expected: str) -> None:
        assert _normalize_pypi_name(raw) == expected


class TestVersionComparison:
    @pytest.mark.parametrize(
        ("latest", "current", "expected"),
        [
            ("1.6.0", "1.4.2", True),
            ("1.4.2", "1.4.2", False),
            ("1.4", "1.4.2", False),
            ("1.4.2", "1.4", True),
            ("v2.0.0", "1.9.9", True),
            ("0.1.9", "0.1.10", False),
            ("abc", "1.0.0", True),
            ("abc", "abc", False),
        ],
    )
    def test_is_newer(self, latest: str, current: str, expected: bool) -> None:
        assert _version_is_newer(latest, current) is expected


class TestDisplayUrl:
    def test_strips_scheme_and_git_suffix(self) -> None:
        assert (
            _display_url("https://github.com/foo/magic.git") == "github.com/foo/magic"
        )

    def test_renders_scp_style_urls(self) -> None:
        assert _display_url("git@github.com:foo/magic.git") == "github.com/foo/magic"


class TestIndexCheck:
    def test_update_available(self) -> None:
        with patch(
            "usecli.shared.upgrades.checker._fetch_pypi_latest",
            return_value="1.6.0",
        ) as fetch:
            status = check(_install())
        fetch.assert_called_once_with("magic-cli")
        assert status.latest == "1.6.0"
        assert status.update_available is True
        assert status.detail == "PyPI"
        assert status.error is None

    def test_up_to_date(self) -> None:
        with patch(
            "usecli.shared.upgrades.checker._fetch_pypi_latest",
            return_value="1.4.2",
        ):
            status = check(_install())
        assert status.update_available is False

    def test_network_error_is_reported(self) -> None:
        with patch(
            "usecli.shared.upgrades.checker._fetch_pypi_latest",
            side_effect=OSError("connection refused"),
        ):
            status = check(_install())
        assert status.latest is None
        assert status.update_available is False
        assert status.error is not None
        assert "Could not reach PyPI" in status.error

    def test_unknown_package_is_reported(self) -> None:
        with patch(
            "usecli.shared.upgrades.checker._fetch_pypi_latest",
            return_value=None,
        ):
            status = check(_install())
        assert status.error is not None
        assert "No release information" in status.error


class TestGitCheck:
    def test_new_remote_commit_is_an_update(self) -> None:
        install = _install(
            source="git",
            url="https://github.com/foo/magic.git",
            revision="main",
            commit="a" * 40,
        )
        new_sha = "b" * 40
        with patch(
            "usecli.shared.upgrades.checker._fetch_git_head",
            return_value=new_sha,
        ) as fetch:
            status = check(install)
        fetch.assert_called_once_with("https://github.com/foo/magic.git", "main")
        assert status.latest == new_sha
        assert status.update_available is True
        assert status.detail == "github.com/foo/magic"

    def test_same_commit_is_up_to_date(self) -> None:
        sha = "a" * 40
        install = _install(
            source="git",
            url="https://github.com/foo/magic.git",
            revision="main",
            commit=sha,
        )
        with patch(
            "usecli.shared.upgrades.checker._fetch_git_head",
            return_value=sha,
        ):
            status = check(install)
        assert status.update_available is False

    def test_missing_url_is_reported(self) -> None:
        install = _install(source="git", revision="main")
        status = check(install)
        assert status.error is not None
        assert "Git URL" in status.error

    def test_unresolvable_branch_is_reported(self) -> None:
        install = _install(
            source="git",
            url="https://github.com/foo/magic.git",
            revision="main",
            commit="a" * 40,
        )
        with patch(
            "usecli.shared.upgrades.checker._fetch_git_head",
            return_value=None,
        ):
            status = check(install)
        assert status.error is not None
        assert "Could not resolve remote branch" in status.error

    def test_ls_remote_failure_is_reported(self) -> None:
        import subprocess

        install = _install(
            source="git",
            url="https://github.com/foo/magic.git",
            revision="main",
            commit="a" * 40,
        )
        with patch(
            "usecli.shared.upgrades.checker._fetch_git_head",
            side_effect=subprocess.SubprocessError("timeout"),
        ):
            status = check(install)
        assert status.error is not None
        assert "Could not query the remote Git repository" in status.error


class TestPinnedChecks:
    def test_tag_install_never_contacts_the_network(self) -> None:
        install = _install(
            source="git",
            url="https://github.com/foo/magic.git",
            revision="v1.2.0",
            commit="a" * 40,
            pinned=True,
            pinned_reason="Git tag (v1.2.0)",
        )
        with patch("usecli.shared.upgrades.checker._fetch_git_head") as fetch:
            status = check(install)
        fetch.assert_not_called()
        assert status.latest is None
        assert status.update_available is False
        assert status.error is None

    def test_editable_install_has_no_remote_check(self) -> None:
        status = check(_install(source="editable", pinned=True))
        assert status.latest is None
        assert status.update_available is False

    def test_frozen_bundle_reports_error(self) -> None:
        status = check(_install(frozen=True, pinned=True))
        assert status.error is not None
        assert "frozen bundle" in status.error

    def test_unknown_source_reports_error(self) -> None:
        status = check(_install(source="unknown"))
        assert status.error is not None
        assert "Could not determine" in status.error


class TestFetchPypiLatest:
    def test_returns_latest_version(self) -> None:
        response = Mock()
        response.read.return_value = b'{"info": {"version": " 2.0.0 "}}'
        with patch(
            "urllib.request.urlopen",
            return_value=Mock(
                __enter__=Mock(return_value=response), __exit__=Mock(return_value=False)
            ),
        ) as urlopen:
            latest = _fetch_pypi_latest("Magic_CLI")
        assert latest == "2.0.0"
        request = urlopen.call_args.args[0]
        assert request.full_url == "https://pypi.org/pypi/magic-cli/json"
        assert urlopen.call_args.kwargs["timeout"] == 10

    def test_non_dict_payload_raises_type_error(self) -> None:
        response = Mock()
        response.read.return_value = b"[1, 2]"
        with (
            patch(
                "urllib.request.urlopen",
                return_value=Mock(
                    __enter__=Mock(return_value=response),
                    __exit__=Mock(return_value=False),
                ),
            ),
            pytest.raises(TypeError, match="Unexpected PyPI response"),
        ):
            _fetch_pypi_latest("magic-cli")

    def test_missing_version_returns_none(self) -> None:
        response = Mock()
        response.read.return_value = b'{"info": {}}'
        with patch(
            "urllib.request.urlopen",
            return_value=Mock(
                __enter__=Mock(return_value=response),
                __exit__=Mock(return_value=False),
            ),
        ):
            latest = _fetch_pypi_latest("magic-cli")
        assert latest is None


class TestFetchGitHead:
    def test_queries_requested_branch(self) -> None:
        with patch(
            "subprocess.run",
            return_value=Mock(returncode=0, stdout="abc123\trefs/heads/main\n"),
        ) as run:
            head = _fetch_git_head("https://github.com/foo/magic.git", "main")
        assert head == "abc123"
        assert run.call_args.args[0] == [
            "git",
            "ls-remote",
            "https://github.com/foo/magic.git",
            "refs/heads/main",
        ]

    def test_queries_head_when_no_revision(self) -> None:
        with patch(
            "subprocess.run",
            return_value=Mock(returncode=0, stdout="def456\tHEAD\n"),
        ) as run:
            head = _fetch_git_head("https://github.com/foo/magic.git", None)
        assert head == "def456"
        assert run.call_args.args[0][-1] == "HEAD"

    def test_failed_ls_remote_returns_none(self) -> None:
        with patch(
            "subprocess.run",
            return_value=Mock(returncode=128, stdout="", stderr="fatal:"),
        ):
            head = _fetch_git_head("https://github.com/foo/magic.git", "main")
        assert head is None

    def test_empty_output_returns_none(self) -> None:
        with patch(
            "subprocess.run",
            return_value=Mock(returncode=0, stdout="", stderr=""),
        ):
            head = _fetch_git_head("https://github.com/foo/magic.git", "main")
        assert head is None


class TestUnsupportedSource:
    def test_unrecognized_source_falls_through(self) -> None:
        status = check(_install(source="carrier-pigeon"))
        assert status.error is not None
        assert "Unsupported installation source" in status.error
        assert status.latest is None
        assert status.update_available is False
