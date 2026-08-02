"""Extended tests for usecli.cli.core.ui.list — utility functions."""

from __future__ import annotations

from unittest.mock import MagicMock

from usecli.cli.core.ui.list import (
    _build_alias_to_primary,
    _format_display_name,
    _get_alias_registry,
    _get_group_alias_registry,
    _get_option_description,
    _order_completion_params,
)


class TestGetAliasRegistry:
    def test_returns_empty_for_no_attribute(self):
        app = MagicMock(spec=[])
        result = _get_alias_registry(app)
        assert result == {}

    def test_returns_registry_when_present(self):
        app = MagicMock()
        app._usecli_aliases = {"cmd": ["alias1"]}
        result = _get_alias_registry(app)
        assert result == {"cmd": ["alias1"]}

    def test_returns_empty_for_non_dict(self):
        app = MagicMock()
        app._usecli_aliases = "not a dict"
        result = _get_alias_registry(app)
        assert result == {}


class TestGetGroupAliasRegistry:
    def test_returns_empty_for_no_attribute(self):
        app = MagicMock(spec=[])
        result = _get_group_alias_registry(app)
        assert result == {}

    def test_returns_registry_when_present(self):
        app = MagicMock()
        app._usecli_group_aliases = {"group": ["alias"]}
        result = _get_group_alias_registry(app)
        assert result == {"group": ["alias"]}


class TestGetOptionDescription:
    def test_returns_show_completion_text(self):
        param = MagicMock()
        param.opts = ["--show-completion"]
        result = _get_option_description(param)
        assert "completion" in result.lower()

    def test_returns_help_text(self):
        param = MagicMock()
        param.opts = ["--verbose"]
        param.help = "Enable verbose mode"
        result = _get_option_description(param)
        assert result == "Enable verbose mode"

    def test_returns_empty_for_no_help(self):
        param = MagicMock()
        param.opts = ["--verbose"]
        param.help = None
        result = _get_option_description(param)
        assert result == ""


class TestOrderCompletionParams:
    def test_returns_params_unchanged_when_no_completion(self):
        p1 = MagicMock()
        p1.opts = ["--verbose"]
        p2 = MagicMock()
        p2.opts = ["--name"]
        result = _order_completion_params([p1, p2])
        assert len(result) == 2

    def test_returns_empty_for_empty_list(self):
        result = _order_completion_params([])
        assert result == []

    def test_reorders_when_show_before_install(self):
        install = MagicMock()
        install.opts = ["--install-completion"]
        show = MagicMock()
        show.opts = ["--show-completion"]
        other = MagicMock()
        other.opts = ["--verbose"]
        result = _order_completion_params([other, show, install])
        # show should be moved before install
        assert result[0].opts == ["--verbose"]


class TestBuildAliasToPrimary:
    def test_builds_mapping(self):
        registry = {"cmd": ["alias1", "alias2"]}
        result = _build_alias_to_primary(registry)
        assert result == {"cmd": "cmd", "alias1": "cmd", "alias2": "cmd"}

    def test_handles_empty_registry(self):
        result = _build_alias_to_primary({})
        assert result == {}

    def test_handles_multiple_commands(self):
        registry = {"cmd1": ["a1"], "cmd2": ["a2"]}
        result = _build_alias_to_primary(registry)
        assert result["cmd1"] == "cmd1"
        assert result["a1"] == "cmd1"
        assert result["cmd2"] == "cmd2"
        assert result["a2"] == "cmd2"


class TestFormatDisplayName:
    def test_returns_name_without_aliases(self):
        assert _format_display_name("cmd", []) == "cmd"

    def test_includes_aliases(self):
        result = _format_display_name("cmd", ["alias1", "alias2"])
        assert result == "cmd, alias1, alias2"

    def test_single_alias(self):
        result = _format_display_name("cmd", ["a"])
        assert result == "cmd, a"
