"""Coverage-focused tests for usecli.cli.commands.defaults.core.utils.

Targets the uncovered ``Path.cwd()`` default branches in ``get_spec_ids``,
``get_change_path``, and ``get_spec_path`` (lines 71, 177, 197) without
modifying source.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from usecli.cli.commands.defaults.core.utils import (
    get_change_path,
    get_spec_ids,
    get_spec_path,
)


class TestGetSpecIdsDefaultsToCwd:
    def test_defaults_to_cwd_when_specs_dir_missing(self, tmp_path):
        with patch("usecli.cli.commands.defaults.core.utils.Path") as mock_path:
            mock_path.cwd.return_value = tmp_path
            mock_path.side_effect = lambda *a: Path(*a) if a else tmp_path
            assert get_spec_ids() == []

    def test_defaults_to_cwd_and_lists_specs(self, tmp_path):
        specs_dir = tmp_path / "usecli" / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec-b").mkdir()
        (specs_dir / "spec-a").mkdir()
        with patch("usecli.cli.commands.defaults.core.utils.Path") as mock_path:
            mock_path.cwd.return_value = tmp_path
            mock_path.side_effect = lambda *a: Path(*a) if a else tmp_path
            assert get_spec_ids() == ["spec-a", "spec-b"]


class TestGetChangePathDefaultsToCwd:
    def test_defaults_to_cwd_when_change_missing(self, tmp_path):
        with patch("usecli.cli.commands.defaults.core.utils.Path") as mock_path:
            mock_path.cwd.return_value = tmp_path
            mock_path.side_effect = lambda *a: Path(*a) if a else tmp_path
            assert get_change_path("nope") is None

    def test_defaults_to_cwd_and_finds_change(self, tmp_path):
        change_dir = tmp_path / "usecli" / "changes" / "my-change"
        change_dir.mkdir(parents=True)
        with patch("usecli.cli.commands.defaults.core.utils.Path") as mock_path:
            mock_path.cwd.return_value = tmp_path
            mock_path.side_effect = lambda *a: Path(*a) if a else tmp_path
            assert get_change_path("my-change") == change_dir


class TestGetSpecPathDefaultsToCwd:
    def test_defaults_to_cwd_when_spec_missing(self, tmp_path):
        with patch("usecli.cli.commands.defaults.core.utils.Path") as mock_path:
            mock_path.cwd.return_value = tmp_path
            mock_path.side_effect = lambda *a: Path(*a) if a else tmp_path
            assert get_spec_path("nope") is None

    def test_defaults_to_cwd_and_finds_spec(self, tmp_path):
        spec_dir = tmp_path / "usecli" / "specs" / "spec-1"
        spec_dir.mkdir(parents=True)
        with patch("usecli.cli.commands.defaults.core.utils.Path") as mock_path:
            mock_path.cwd.return_value = tmp_path
            mock_path.side_effect = lambda *a: Path(*a) if a else tmp_path
            assert get_spec_path("spec-1") == spec_dir
