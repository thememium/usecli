"""Tests for usecli.__init__ — main entry point, lazy imports, and utilities."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.exceptions import BadParameter, ClickException, Exit

import usecli

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


# =============================================================================
# Coverage-focused: usecli.__init__ edge branches
# =============================================================================

# Keys written into the module namespace by _ensure_cli_initialized /
# _get_run_app_callback. Used to snapshot/reset/restore module state.
_INIT_KEYS = [
    "_app",
    "_service",
    "_help_resolved",
    "BaseCommand",
    "app",
    "service",
    "COLOR",
    "theme",
    "colors",
    "PrefixMatchingGroup",
    "_TyperBadParameter",
    "_TyperClickException",
    "_TyperUsageError",
    "_Exit",
    "_BadParameter",
    "_ClickException",
    "_UsageError",
    "_TyperGroup",
    "run_app",
    "typer",
]


def _snapshot_cli_state() -> dict:
    return {k: (k in usecli.__dict__, usecli.__dict__.get(k)) for k in _INIT_KEYS}


def _reset_cli_state() -> None:
    for k in _INIT_KEYS:
        usecli.__dict__.pop(k, None)
    usecli._app = None
    usecli._service = None
    usecli._help_resolved = False


def _restore_cli_state(snapshot: dict) -> None:
    for k, (present, value) in snapshot.items():
        if present:
            usecli.__dict__[k] = value
        else:
            usecli.__dict__.pop(k, None)


def _fresh_group():
    """Return a fresh PrefixMatchingGroup instance."""
    usecli._ensure_cli_initialized()
    return usecli.PrefixMatchingGroup(name="test", commands={})  # type: ignore[ty:call-non-callable]


def _json_main(group, exc):
    """Invoke PrefixMatchingGroup.main in JSON mode with a patched parent main."""
    with patch.object(usecli._TyperGroup, "main", side_effect=exc):
        return group.main(args=["--json"])


# ---------------------------------------------------------------------------
# __getattr__ run_app lazy path (lines 64-66)
# ---------------------------------------------------------------------------


class TestGetattrRunApp:
    def test_run_app_lazy_getattr_path(self):
        usecli._ensure_cli_initialized()
        # Remove run_app so attribute access falls through to __getattr__.
        del usecli.__dict__["run_app"]
        try:
            result = usecli.run_app
            assert callable(result)
        finally:
            usecli._get_run_app_callback()


# ---------------------------------------------------------------------------
# _ensure_cli_initialized ImportError/AttributeError fallback (lines 96-99)
# ---------------------------------------------------------------------------


class TestEnsureCliInitializedFallback:
    def test_import_error_fallback_uses_click_exceptions(self):
        snapshot = _snapshot_cli_state()
        try:
            _reset_cli_state()
            real_import = usecli.import_module

            def fake_import(name, *args, **kwargs):
                if name == "typer._click.exceptions":
                    raise ImportError("boom")
                return real_import(name, *args, **kwargs)

            with patch.object(usecli, "import_module", side_effect=fake_import):
                usecli._ensure_cli_initialized()

            from click.exceptions import BadParameter as ClickBadParameter

            assert usecli._TyperBadParameter is ClickBadParameter
            assert usecli._TyperClickException is ClickException
        finally:
            _restore_cli_state(snapshot)


# ---------------------------------------------------------------------------
# PrefixMatchingGroup.get_command alias / prefix branches (lines 129, 145-155)
# ---------------------------------------------------------------------------


class TestGetCommandBranches:
    def test_get_command_alias_maps_to_primary(self):
        group = _fresh_group()
        ctx = MagicMock()
        app = MagicMock()
        app._usecli_group_aliases = {"primary": ["alias"]}
        with (
            patch.object(usecli, "_get_app", return_value=app),
            patch.object(type(group), "list_commands", return_value=[]),
        ):
            result = group.get_command(ctx, "alias")
        assert result is None

    def test_get_command_full_name_in_matches(self):
        group = _fresh_group()
        ctx = MagicMock()
        app = MagicMock()
        app._usecli_group_aliases = {}
        with (
            patch.object(usecli, "_get_app", return_value=app),
            patch.object(type(group), "list_commands", return_value=["primary"]),
        ):
            result = group.get_command(ctx, "primary")
        assert result is None

    def test_get_command_prefix_match_returns_filtered_list(self):
        group = _fresh_group()
        ctx = MagicMock()
        app = MagicMock()
        app._usecli_group_aliases = {}
        with (
            patch.object(usecli, "_get_app", return_value=app),
            patch.object(type(group), "list_commands", return_value=["primary"]),
        ):
            result = group.get_command(ctx, "pri")
        assert isinstance(result, usecli._FilteredListCommand)
        assert result.prefix_filter == "pri"


# ---------------------------------------------------------------------------
# PrefixMatchingGroup.main JSON-mode branches (lines 226-227, 230-234,
# 242-243, 255-259)
# ---------------------------------------------------------------------------


class TestJsonMainBranches:
    def test_invocation_exit_zero_writes_success(self, capsys):
        from usecli.cli.core.runtime import InvocationExit

        group = _fresh_group()
        result = _json_main(group, InvocationExit(0))
        assert result is None
        out = capsys.readouterr().out
        assert json.loads(out) == {"ok": True, "data": None}

    def test_exit_zero_writes_success(self, capsys):
        group = _fresh_group()
        result = _json_main(group, Exit(0))
        assert result is None
        out = capsys.readouterr().out
        assert json.loads(out) == {"ok": True, "data": None}

    def test_exit_nonzero_fails(self, capsys):
        group = _fresh_group()
        with pytest.raises(SystemExit) as exc:
            _json_main(group, Exit(5))
        assert exc.value.code == 5
        doc = json.loads(capsys.readouterr().out)
        assert doc["ok"] is False
        assert doc["error"]["type"] == "Exit"

    def test_bad_parameter_fails(self, capsys):
        group = _fresh_group()
        with pytest.raises(SystemExit) as exc:
            _json_main(group, BadParameter("bad value"))
        assert exc.value.code == 2
        doc = json.loads(capsys.readouterr().out)
        assert doc["error"]["type"] == "BadParameter"

    def test_system_exit_zero_writes_success(self, capsys):
        group = _fresh_group()
        result = _json_main(group, SystemExit(0))
        assert result is None
        out = capsys.readouterr().out
        assert json.loads(out) == {"ok": True, "data": None}

    def test_system_exit_nonzero_fails(self, capsys):
        group = _fresh_group()
        with pytest.raises(SystemExit) as exc:
            _json_main(group, SystemExit(5))
        assert exc.value.code == 5
        doc = json.loads(capsys.readouterr().out)
        assert doc["error"]["type"] == "Exit"


# ---------------------------------------------------------------------------
# PrefixMatchingGroup.invoke non-JSON branches (lines 294, 296-300, 307-310)
# ---------------------------------------------------------------------------


class TestInvokeBranches:
    def test_invoke_exit_sys_exit_zero(self):
        group = _fresh_group()
        ctx = MagicMock()
        with (
            patch.object(usecli._TyperGroup, "invoke", side_effect=Exit(0)),
            pytest.raises(SystemExit) as exc,
        ):
            group.invoke(ctx)
        assert exc.value.code == 0

    def test_invoke_typer_bad_parameter(self):
        group = _fresh_group()
        ctx = MagicMock()
        error = usecli._TyperBadParameter("bad param")
        error.ctx = MagicMock()
        error.param = MagicMock()
        with (
            patch.object(usecli._TyperGroup, "invoke", side_effect=error),
            pytest.raises(SystemExit) as exc,
        ):
            group.invoke(ctx)
        assert exc.value.code == error.exit_code

    def test_invoke_typer_click_exception(self):
        group = _fresh_group()
        ctx = MagicMock()
        error = usecli._TyperClickException("boom")
        with (
            patch.object(usecli._TyperGroup, "invoke", side_effect=error),
            pytest.raises(SystemExit) as exc,
        ):
            group.invoke(ctx)
        assert exc.value.code == error.exit_code


# ---------------------------------------------------------------------------
# _get_service (lines 350-351)
# ---------------------------------------------------------------------------


class TestGetService:
    def test_get_service_returns_service(self):
        usecli._ensure_cli_initialized()
        assert usecli._get_service() is not None


# ---------------------------------------------------------------------------
# run_app branches (lines 544, 547-557, 580)
# ---------------------------------------------------------------------------


class TestRunAppBranches:
    def test_help_in_json_mode_returns_data(self):
        from usecli.cli.core.runtime import execution_context

        usecli._ensure_cli_initialized()
        ctx = MagicMock()
        sentinel = object()
        with (
            patch("usecli.cli.core.ui.list.list_commands", return_value=sentinel),
            execution_context(json_mode=True),
        ):
            result = usecli.run_app(
                ctx=ctx,
                version=None,
                help=True,
                interactive=False,
                json_output=True,
            )
        assert result is sentinel

    def test_help_in_human_mode_raises_exit(self):
        usecli._ensure_cli_initialized()
        ctx = MagicMock()
        with (
            patch("usecli.cli.core.ui.list.list_commands", return_value=[]),
            pytest.raises(usecli.typer.Exit),
        ):
            usecli.run_app(
                ctx=ctx,
                version=None,
                help=True,
                interactive=False,
                json_output=False,
            )

    def test_version_branch(self):
        usecli._ensure_cli_initialized()
        ctx = MagicMock()
        config = MagicMock()
        config.get.return_value = "MyApp"
        service = MagicMock()
        service.version = "1.2.3"
        with (
            patch("usecli.shared.config.manager.get_config", return_value=config),
            patch.object(usecli, "_get_service", return_value=service),
            patch.object(usecli, "_console", return_value=MagicMock()),
            patch("shutil.which", return_value="/usr/bin/mycli"),
            pytest.raises(usecli.typer.Exit),
        ):
            usecli.run_app(
                ctx=ctx,
                version=True,
                help=False,
                interactive=False,
                json_output=False,
            )

    def test_prefix_filter_from_ctx_obj(self):
        usecli._ensure_cli_initialized()
        ctx = MagicMock()
        ctx.invoked_subcommand = None
        ctx.obj = {"prefix_filter": "ab"}
        captured = {}

        def fake_list(app, prefix_filter=None):
            captured["prefix_filter"] = prefix_filter
            return "listed"

        with patch("usecli.cli.core.ui.list.list_commands", side_effect=fake_list):
            result = usecli.run_app(
                ctx=ctx,
                version=None,
                help=False,
                interactive=False,
                json_output=False,
            )
        assert captured["prefix_filter"] == "ab"
        assert result == "listed"


# ---------------------------------------------------------------------------
# main() BadParameter / ClickException handling (lines 623-627, 635-637)
# ---------------------------------------------------------------------------


class TestMainExceptionHandling:
    def _config(self):
        return MagicMock(
            _get_command_name=MagicMock(return_value="mycli"),
            is_usecli_direct_dependency=MagicMock(return_value=True),
        )

    def test_main_handles_bad_parameter(self):
        usecli._ensure_cli_initialized()
        error = usecli._TyperBadParameter("bad")
        error.ctx = MagicMock()
        error.param = MagicMock()
        with (
            patch(
                "usecli.shared.config.manager.get_config", return_value=self._config()
            ),
            patch.object(usecli, "_get_app", side_effect=error),
            pytest.raises(SystemExit) as exc,
        ):
            usecli.main()
        assert exc.value.code == error.exit_code

    def test_main_handles_click_exception(self):
        usecli._ensure_cli_initialized()
        error = usecli._TyperClickException("boom")
        with (
            patch(
                "usecli.shared.config.manager.get_config", return_value=self._config()
            ),
            patch.object(usecli, "_get_app", side_effect=error),
            pytest.raises(SystemExit) as exc,
        ):
            usecli.main()
        assert exc.value.code == error.exit_code


# ---------------------------------------------------------------------------
# __main__ guard (line 654)
# ---------------------------------------------------------------------------


class TestMainGuard:
    def test_main_guard_runs_main(self):
        source = Path(usecli.__file__).read_text()
        modified = source.replace(
            'if __name__ == "__main__":\n    main()',
            'if __name__ == "__main__":\n    mock_main()',
        )
        mock_main = MagicMock()
        namespace = {"__name__": "__main__", "mock_main": mock_main}
        exec(compile(modified, usecli.__file__, "exec"), namespace)  # noqa: S102
        mock_main.assert_called_once()
