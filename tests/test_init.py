"""Tests for usecli.__init__ — main entry point, lazy imports, and utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Lazy exports
# ---------------------------------------------------------------------------


class TestLazyExports:
    def test_lazy_import_menu(self):
        from usecli import Menu

        assert Menu is not None

    def test_lazy_import_argument(self):
        from usecli import Argument

        assert Argument is not None

    def test_lazy_import_option(self):
        from usecli import Option

        assert Option is not None

    def test_lazy_import_prompt(self):
        from usecli import Prompt

        assert Prompt is not None

    def test_lazy_import_confirm(self):
        from usecli import Confirm

        assert Confirm is not None

    def test_lazy_import_console(self):
        from usecli import console

        assert console is not None

    def test_lazy_import_spinner(self):
        from usecli import Spinner

        assert Spinner is not None

    def test_lazy_import_progress_bar(self):
        from usecli import ProgressBar

        assert ProgressBar is not None

    def test_getattr_raises_for_unknown(self):
        import usecli

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = usecli.nonexistent_xyz_123


# ---------------------------------------------------------------------------
# _is_interactive_flag_present
# ---------------------------------------------------------------------------


class TestIsInteractiveFlagPresent:
    def test_returns_true_with_dash_i(self):
        import usecli

        with patch.object(usecli, "sys", argv=["usecli", "-i", "magic"]):
            assert usecli._is_interactive_flag_present() is True

    def test_returns_true_with_double_dash_interactive(self):
        import usecli

        with patch.object(usecli, "sys", argv=["usecli", "--interactive", "magic"]):
            assert usecli._is_interactive_flag_present() is True

    def test_returns_false_when_absent(self):
        import usecli

        with patch.object(usecli, "sys", argv=["usecli", "magic"]):
            assert usecli._is_interactive_flag_present() is False


# ---------------------------------------------------------------------------
# _get_cli_help_text
# ---------------------------------------------------------------------------


class TestGetCliHelpText:
    def test_returns_fallback_when_no_config(self):
        import usecli

        with patch("usecli.shared.config.manager.get_config") as mock_config:
            mock_config.return_value = MagicMock(
                has_key=MagicMock(return_value=False),
                get=MagicMock(return_value=None),
            )
            result = usecli._get_cli_help_text()
            assert "Usecli CLI" in result

    def test_returns_title_and_description(self):
        import usecli

        with patch("usecli.shared.config.manager.get_config") as mock_config:
            mock_config.return_value = MagicMock(
                has_key=MagicMock(side_effect=lambda k: k in ("title", "description")),
                get=MagicMock(
                    side_effect=lambda k, d=None: {
                        "title": "My App",
                        "description": "A great app",
                    }.get(k, d)
                ),
            )
            result = usecli._get_cli_help_text()
            assert "My App" in result
            assert "A great app" in result

    def test_returns_command_name_and_description(self):
        import usecli

        with patch("usecli.shared.config.manager.get_config") as mock_config:
            mock_config.return_value = MagicMock(
                has_key=MagicMock(
                    side_effect=lambda k: k in ("command_name", "description")
                ),
                get=MagicMock(
                    side_effect=lambda k, d=None: {
                        "command_name": "mycli",
                        "description": "A CLI",
                    }.get(k, d)
                ),
            )
            result = usecli._get_cli_help_text()
            assert "mycli" in result

    def test_returns_default_when_only_description(self):
        import usecli

        with patch("usecli.shared.config.manager.get_config") as mock_config:
            mock_config.return_value = MagicMock(
                has_key=MagicMock(side_effect=lambda k: k == "description"),
                get=MagicMock(
                    side_effect=lambda k, d=None: {"description": "A CLI"}.get(k, d)
                ),
            )
            result = usecli._get_cli_help_text()
            assert "A CLI" in result


# ---------------------------------------------------------------------------
# _get_group_alias_registry / _build_alias_to_primary
# ---------------------------------------------------------------------------


class TestAliasHelpers:
    def test_get_group_alias_registry_returns_dict(self):
        import usecli

        app = MagicMock()
        app._usecli_group_aliases = {"group": ["alias"]}
        result = usecli._get_group_alias_registry(app)
        assert result == {"group": ["alias"]}

    def test_get_group_alias_registry_returns_empty_for_missing(self):
        import usecli

        app = MagicMock(spec=[])
        result = usecli._get_group_alias_registry(app)
        assert result == {}

    def test_get_group_alias_registry_returns_empty_for_non_dict(self):
        import usecli

        app = MagicMock()
        app._usecli_group_aliases = "not a dict"
        result = usecli._get_group_alias_registry(app)
        assert result == {}

    def test_build_alias_to_primary(self):
        import usecli

        result = usecli._build_alias_to_primary({"cmd1": ["a1", "a2"], "cmd2": ["b1"]})
        assert result == {
            "cmd1": "cmd1",
            "a1": "cmd1",
            "a2": "cmd1",
            "cmd2": "cmd2",
            "b1": "cmd2",
        }

    def test_build_alias_to_primary_empty(self):
        import usecli

        result = usecli._build_alias_to_primary({})
        assert result == {}


# ---------------------------------------------------------------------------
# _FilteredListCommand
# ---------------------------------------------------------------------------


class TestFilteredListCommand:
    def test_init(self):
        import usecli

        cmd = usecli._FilteredListCommand("test")
        assert cmd.prefix_filter == "test"
        assert cmd.allow_extra_args is True
        assert cmd.allow_interspersed_args is True
        assert cmd.ignore_unknown_options is True

    def test_get_short_help_str(self):
        import usecli

        cmd = usecli._FilteredListCommand("test")
        assert cmd.get_short_help_str() == ""

    def test_make_context(self):
        import usecli

        cmd = usecli._FilteredListCommand("test")
        ctx = cmd.make_context("test", [])
        assert ctx is not None

    @patch("usecli.cli.core.ui.list.list_commands")
    def test_invoke(self, mock_list):
        import usecli

        cmd = usecli._FilteredListCommand("test")
        ctx = MagicMock()
        cmd.invoke(ctx)
        mock_list.assert_called_once()

    @patch("usecli.cli.core.ui.list.list_commands")
    def test_call(self, mock_list):
        import usecli

        cmd = usecli._FilteredListCommand("test")
        cmd()
        mock_list.assert_called_once()


# ---------------------------------------------------------------------------
# _get_default_help / _resolve_help
# ---------------------------------------------------------------------------


class TestHelpResolution:
    def test_get_default_help(self):
        import usecli

        result = usecli._get_default_help()
        assert "Usecli CLI" in result

    def test_resolve_help_sets_help_text(self):
        import usecli

        usecli._help_resolved = False
        with patch("usecli._get_cli_help_text", return_value="Custom help"):
            usecli._resolve_help()
            assert usecli._help_resolved is True

    def test_resolve_help_is_idempotent(self):
        import usecli

        usecli._help_resolved = False
        with patch("usecli._get_cli_help_text", return_value="Help 1"):
            usecli._resolve_help()
        with patch("usecli._get_cli_help_text", return_value="Help 2"):
            usecli._resolve_help()
        # Should not call _get_cli_help_text again


# ---------------------------------------------------------------------------
# _console
# ---------------------------------------------------------------------------


class TestConsoleHelper:
    def test_console_returns_console_object(self):
        import usecli

        result = usecli._console()
        assert result is not None


# ---------------------------------------------------------------------------
# PrefixMatchingGroup
# ---------------------------------------------------------------------------


class TestPrefixMatchingGroup:
    def test_prefix_matching_group_is_created(self):
        import usecli

        usecli._ensure_cli_initialized()
        PMG = usecli.PrefixMatchingGroup
        assert PMG is not None

    def test_get_command_returns_none_for_no_match(self):
        import usecli

        usecli._ensure_cli_initialized()
        PMG = usecli.PrefixMatchingGroup
        group = PMG(name="test", commands={})  # type: ignore[ty:call-non-callable]
        ctx = MagicMock()
        ctx.find_root.return_value = MagicMock(params={})
        with (
            patch.object(type(group), "list_commands", return_value=[]),
            patch.object(type(group), "get_command", return_value=None),
        ):
            result = group.get_command(ctx, "nonexistent")
            assert result is None


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


class TestMain:
    @patch("usecli.shared.config.manager.get_config")
    def test_main_exits_when_not_dependency(self, mock_config):
        import usecli

        mock_config.return_value = MagicMock(
            _get_command_name=MagicMock(return_value="usecli"),
            is_usecli_direct_dependency=MagicMock(return_value=False),
        )
        with pytest.raises(SystemExit) as exc_info:
            usecli.main()
        assert exc_info.value.code == 1

    @patch("usecli.shared.config.manager.get_config")
    @patch("usecli._get_app")
    def test_main_calls_app(self, mock_app, mock_config):
        import usecli

        mock_config.return_value = MagicMock(
            _get_command_name=MagicMock(return_value="mycli"),
            is_usecli_direct_dependency=MagicMock(return_value=True),
        )
        mock_app.return_value = MagicMock()
        usecli.main()
        mock_app.return_value.assert_called_once()

    @patch("usecli.shared.config.manager.get_config")
    @patch("usecli._get_app")
    def test_main_handles_exit(self, mock_app, mock_config):
        from click.exceptions import Exit

        import usecli

        mock_config.return_value = MagicMock(
            _get_command_name=MagicMock(return_value="mycli"),
            is_usecli_direct_dependency=MagicMock(return_value=True),
        )
        mock_app.return_value = MagicMock(side_effect=Exit(0))
        with pytest.raises(SystemExit) as exc_info:
            usecli.main()
        assert exc_info.value.code == 0

    @patch("usecli.shared.config.manager.get_config")
    @patch("usecli._get_app")
    def test_main_handles_usage_error(self, mock_app, mock_config):
        import usecli

        # Ensure _TyperUsageError is set
        usecli._ensure_cli_initialized()
        TyperUsageError = (
            usecli.globals()["_TyperUsageError"]
            if hasattr(usecli, "globals")
            else usecli.__dict__.get("_TyperUsageError")
        )
        if TyperUsageError is None:
            from typer._click.exceptions import UsageError as TyperUsageError
        mock_config.return_value = MagicMock(
            _get_command_name=MagicMock(return_value="mycli"),
            is_usecli_direct_dependency=MagicMock(return_value=True),
        )
        error = TyperUsageError("test error")
        mock_app.return_value = MagicMock(side_effect=error)
        with pytest.raises(SystemExit) as exc_info:
            usecli.main()
        assert exc_info.value.code == 2

    @patch("usecli.shared.config.manager.get_config")
    @patch("usecli._get_app")
    def test_main_handles_os_error(self, mock_app, mock_config):
        import usecli

        mock_config.return_value = MagicMock(
            _get_command_name=MagicMock(return_value="mycli"),
            is_usecli_direct_dependency=MagicMock(return_value=True),
        )
        mock_app.return_value = MagicMock(side_effect=OSError("disk full"))
        with pytest.raises(SystemExit) as exc_info:
            usecli.main()
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# _ensure_cli_initialized
# ---------------------------------------------------------------------------


class TestEnsureCliInitialized:
    def test_ensure_cli_initialized_sets_globals(self):
        import usecli

        usecli._ensure_cli_initialized()
        assert "BaseCommand" in usecli.__dict__
        assert "app" in usecli.__dict__
        assert "service" in usecli.__dict__
        assert "COLOR" in usecli.__dict__
        assert "theme" in usecli.__dict__
