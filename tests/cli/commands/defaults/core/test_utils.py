"""Tests for usecli.cli.commands.defaults.core.utils — shared CLI utilities."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from usecli.cli.commands.defaults.core.utils import (
    find_usecli_root,
    format_relative_time,
    get_active_change_ids,
    get_change_path,
    get_spec_ids,
    get_spec_path,
    is_interactive,
    validate_change_name,
)

# ---------------------------------------------------------------------------
# is_interactive
# ---------------------------------------------------------------------------


class TestIsInteractive:
    def test_returns_true_when_stdin_is_tty(self):
        with patch.object(sys.stdin, "isatty", return_value=True):
            assert is_interactive() is True

    def test_returns_false_when_stdin_is_not_tty(self):
        with patch.object(sys.stdin, "isatty", return_value=False):
            assert is_interactive() is False


# ---------------------------------------------------------------------------
# get_active_change_ids
# ---------------------------------------------------------------------------


class TestGetActiveChangeIds:
    def test_returns_empty_when_changes_dir_missing(self, tmp_path):
        assert get_active_change_ids(tmp_path) == []

    def test_returns_sorted_directory_names(self, tmp_path):
        changes_dir = tmp_path / "usecli" / "changes"
        changes_dir.mkdir(parents=True)
        (changes_dir / "beta").mkdir()
        (changes_dir / "alpha").mkdir()
        (changes_dir / "gamma").mkdir()

        result = get_active_change_ids(tmp_path)
        assert result == ["alpha", "beta", "gamma"]

    def test_excludes_archive_directory(self, tmp_path):
        changes_dir = tmp_path / "usecli" / "changes"
        changes_dir.mkdir(parents=True)
        (changes_dir / "archive").mkdir()
        (changes_dir / "active-item").mkdir()

        result = get_active_change_ids(tmp_path)
        assert result == ["active-item"]

    def test_ignores_files(self, tmp_path):
        changes_dir = tmp_path / "usecli" / "changes"
        changes_dir.mkdir(parents=True)
        (changes_dir / "readme.txt").write_text("not a change")
        (changes_dir / "real-change").mkdir()

        result = get_active_change_ids(tmp_path)
        assert result == ["real-change"]

    def test_defaults_to_cwd(self, tmp_path):
        with patch("usecli.cli.commands.defaults.core.utils.Path") as mock_path:
            mock_path.cwd.return_value = tmp_path
            # Re-construct Path properly for sub-paths
            mock_path.side_effect = lambda *a: Path(*a) if a else tmp_path
            result = get_active_change_ids()
            assert result == []


# ---------------------------------------------------------------------------
# get_spec_ids
# ---------------------------------------------------------------------------


class TestGetSpecIds:
    def test_returns_empty_when_specs_dir_missing(self, tmp_path):
        assert get_spec_ids(tmp_path) == []

    def test_returns_sorted_spec_names(self, tmp_path):
        specs_dir = tmp_path / "usecli" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec-b").mkdir()
        (specs_dir / "spec-a").mkdir()

        result = get_spec_ids(tmp_path)
        assert result == ["spec-a", "spec-b"]

    def test_ignores_files_in_specs_dir(self, tmp_path):
        specs_dir = tmp_path / "usecli" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "notes.md").write_text("not a spec")
        (specs_dir / "real-spec").mkdir()

        result = get_spec_ids(tmp_path)
        assert result == ["real-spec"]


# ---------------------------------------------------------------------------
# validate_change_name
# ---------------------------------------------------------------------------


class TestValidateChangeName:
    def test_valid_simple_name(self):
        valid, msg = validate_change_name("my-change")
        assert valid is True
        assert msg == ""

    def test_valid_with_numbers(self):
        valid, _msg = validate_change_name("fix-123")
        assert valid is True

    def test_empty_name_rejected(self):
        valid, msg = validate_change_name("")
        assert valid is False
        assert "empty" in msg.lower()

    def test_uppercase_rejected(self):
        valid, msg = validate_change_name("MyChange")
        assert valid is False
        assert "lowercase" in msg.lower()

    def test_underscores_rejected(self):
        valid, _msg = validate_change_name("my_change")
        assert valid is False

    def test_leading_hyphen_rejected(self):
        valid, msg = validate_change_name("-leading")
        assert valid is False
        assert "start or end" in msg.lower()

    def test_trailing_hyphen_rejected(self):
        valid, msg = validate_change_name("trailing-")
        assert valid is False
        assert "start or end" in msg.lower()

    def test_consecutive_hyphens_rejected(self):
        valid, msg = validate_change_name("a--b")
        assert valid is False
        assert "consecutive" in msg.lower()

    def test_special_characters_rejected(self):
        valid, _msg = validate_change_name("change@home")
        assert valid is False


# ---------------------------------------------------------------------------
# format_relative_time
# ---------------------------------------------------------------------------


class TestFormatRelativeTime:
    def test_just_now(self):
        now = datetime.now(tz=timezone.utc)
        assert format_relative_time(now) == "just now"

    def test_minutes_ago_singular(self):
        ts = datetime.now(tz=timezone.utc) - timedelta(minutes=1)
        result = format_relative_time(ts)
        assert result == "1 minute ago"

    def test_minutes_ago_plural(self):
        ts = datetime.now(tz=timezone.utc) - timedelta(minutes=5)
        result = format_relative_time(ts)
        assert result == "5 minutes ago"

    def test_hours_ago_singular(self):
        ts = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        result = format_relative_time(ts)
        assert result == "1 hour ago"

    def test_hours_ago_plural(self):
        ts = datetime.now(tz=timezone.utc) - timedelta(hours=3)
        result = format_relative_time(ts)
        assert result == "3 hours ago"

    def test_days_ago_singular(self):
        ts = datetime.now(tz=timezone.utc) - timedelta(days=1)
        result = format_relative_time(ts)
        assert result == "1 day ago"

    def test_days_ago_plural(self):
        ts = datetime.now(tz=timezone.utc) - timedelta(days=15)
        result = format_relative_time(ts)
        assert result == "15 days ago"

    def test_months_ago(self):
        ts = datetime.now(tz=timezone.utc) - timedelta(days=90)
        result = format_relative_time(ts)
        assert "months ago" in result or "month ago" in result

    def test_years_ago(self):
        ts = datetime.now(tz=timezone.utc) - timedelta(days=400)
        result = format_relative_time(ts)
        assert "years ago" in result or "year ago" in result


# ---------------------------------------------------------------------------
# find_usecli_root
# ---------------------------------------------------------------------------


class TestFindUsecliRoot:
    def test_finds_root_with_usecli_dir(self, tmp_path):
        project = tmp_path / "project"
        (project / "usecli").mkdir(parents=True)
        assert find_usecli_root(project) == project

    def test_finds_root_in_parent(self, tmp_path):
        project = tmp_path / "project"
        nested = project / "src" / "deep"
        (project / "usecli").mkdir(parents=True)
        nested.mkdir(parents=True)
        assert find_usecli_root(nested) == project

    def test_returns_none_when_not_found(self, tmp_path):
        # tmp_path has no "usecli" directory anywhere
        assert find_usecli_root(tmp_path) is None

    def test_defaults_to_cwd(self, tmp_path):
        with patch("usecli.cli.commands.defaults.core.utils.Path") as mock_path:
            mock_path.cwd.return_value = tmp_path
            mock_path.side_effect = lambda *a: Path(*a) if a else tmp_path
            result = find_usecli_root()
            assert result is None


# ---------------------------------------------------------------------------
# get_change_path / get_spec_path
# ---------------------------------------------------------------------------


class TestGetChangePath:
    def test_returns_path_when_exists(self, tmp_path):
        change_dir = tmp_path / "usecli" / "changes" / "my-change"
        change_dir.mkdir(parents=True)
        assert get_change_path("my-change", tmp_path) == change_dir

    def test_returns_none_when_missing(self, tmp_path):
        assert get_change_path("nope", tmp_path) is None


class TestGetSpecPath:
    def test_returns_path_when_exists(self, tmp_path):
        spec_dir = tmp_path / "usecli" / "specs" / "spec-1"
        spec_dir.mkdir(parents=True)
        assert get_spec_path("spec-1", tmp_path) == spec_dir

    def test_returns_none_when_missing(self, tmp_path):
        assert get_spec_path("nope", tmp_path) is None


# ---------------------------------------------------------------------------
# _LazyConsole
# ---------------------------------------------------------------------------


class TestLazyConsole:
    def test_lazy_console_proxies_to_rich(self):
        from usecli.cli.commands.defaults.core.utils import console

        # Accessing a method should trigger lazy initialization
        assert hasattr(console, "print")
        assert callable(console.print)

    def test_lazy_console_caches_instance(self):
        from usecli.cli.commands.defaults.core.utils import _LazyConsole

        lc = _LazyConsole()
        # First access initializes
        _ = lc.print
        assert lc._console is not None
        # Second access reuses
        _ = lc.print
        assert lc._console is not None
