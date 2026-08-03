"""Coverage-focused tests for usecli.__init__.

These tests target specific uncovered branches in ``src/usecli/__init__.py``
without modifying any source code. They follow the conventions established in
``tests/test_init.py`` (direct ``import usecli`` + ``patch``) and
``tests/cli/core/test_json_output.py`` (JSON mode via ``PrefixMatchingGroup.main``).

Module state is snapshotted/reset/restored around tests that force
``_ensure_cli_initialized`` to re-run, so tests never depend on execution order.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.exceptions import BadParameter, ClickException, Exit

import usecli

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
