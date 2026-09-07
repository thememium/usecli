"""Tests for the built-in `upgrade` command."""

from __future__ import annotations

from typing import Any
from unittest.mock import Mock, patch

import pytest

from usecli.cli.commands.defaults.base.upgrade_command import UpgradeCommand
from usecli.cli.core.exceptions.base import UsecliError
from usecli.cli.core.runtime import execution_context
from usecli.shared.config.manager import reset_config
from usecli.shared.upgrades.checker import UpgradeStatus
from usecli.shared.upgrades.discovery import InstallInfo
from usecli.shared.upgrades.installer import UpgradeResult


@pytest.fixture(autouse=True)
def isolated_config(tmp_path: Any, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    reset_config()
    yield
    reset_config()


def _install(**overrides: Any) -> InstallInfo:
    defaults: dict[str, Any] = {
        "package": "magic-cli",
        "version": "1.4.2",
        "source": "index",
        "installer": "uv",
    }
    defaults.update(overrides)
    return InstallInfo(**defaults)


def _status(
    install: InstallInfo,
    latest: str | None = "1.6.0",
    update_available: bool = True,
) -> UpgradeStatus:
    return UpgradeStatus(
        install=install,
        latest=latest,
        update_available=update_available,
        detail="PyPI",
    )


def _patched_service(
    install: InstallInfo, status: UpgradeStatus, result: UpgradeResult | None = None
):
    service = Mock()
    service.discover.return_value = install
    service.check.return_value = status
    service.upgrade.return_value = result or UpgradeResult(success=True)
    return service


class TestCommandMetadata:
    def test_signature_and_description(self) -> None:
        command = UpgradeCommand.__new__(UpgradeCommand)
        assert command.signature() == "upgrade"
        assert command.description() == (
            "Upgrade the application to the latest version"
        )

    def test_visible_by_default(self) -> None:
        assert UpgradeCommand.__new__(UpgradeCommand).visible() is True

    def test_hidden_via_config(self, tmp_path: Any) -> None:
        (tmp_path / "usecli.config.toml").write_text(
            "[usecli.upgrade]\nenabled = false\n"
        )
        assert UpgradeCommand.__new__(UpgradeCommand).visible() is False

    def test_registers_as_upgrade(self, mock_typer_app: Any) -> None:
        UpgradeCommand(mock_typer_app)
        names = [
            call.kwargs.get("name") for call in mock_typer_app.command.call_args_list
        ]
        assert "upgrade" in names


class TestCheckMode:
    def test_json_payload_reports_update(self) -> None:
        install = _install()
        service = _patched_service(install, _status(install))
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=True),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle(check=True)
        assert data["mode"] == "check"
        assert data["package"] == "magic-cli"
        assert data["current"] == "1.4.2"
        assert data["latest"] == "1.6.0"
        assert data["source"] == "index"
        assert data["update_available"] is True
        assert data["pinned"] is False
        service.upgrade.assert_not_called()

    def test_json_payload_reports_up_to_date(self) -> None:
        install = _install()
        service = _patched_service(
            install, _status(install, latest="1.4.2", update_available=False)
        )
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=True),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle(check=True)
        assert data["update_available"] is False

    def test_git_check_exposes_vcs_fields(self) -> None:
        install = _install(
            source="git",
            url="https://github.com/foo/magic.git",
            revision="main",
            commit="a" * 40,
        )
        service = _patched_service(
            install,
            UpgradeStatus(
                install=install,
                latest="b" * 40,
                update_available=True,
                detail="github.com/foo/magic",
            ),
        )
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=True),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle(check=True)
        assert data["source"] == "git"
        assert data["revision"] == "main"
        assert data["commit"] == "a" * 40
        assert data["latest"] == "b" * 40

    def test_check_error_raises(self) -> None:
        install = _install()
        service = _patched_service(
            install,
            UpgradeStatus(install=install, error="Could not reach PyPI: boom"),
        )
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=True),
            pytest.raises(UsecliError, match="Could not reach PyPI"),
        ):
            UpgradeCommand.__new__(UpgradeCommand).handle(check=True)


class TestApplyMode:
    def test_successful_upgrade(self) -> None:
        install = _install()
        result = UpgradeResult(success=True)
        service = _patched_service(install, _status(install), result)
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=True),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle()
        assert data["upgraded"] is True
        assert data["mode"] == "apply"
        service.upgrade.assert_called_once_with(
            install, service.discover.call_args.args[0]
        )

    def test_confirmation_skipped_with_force(self) -> None:
        install = _install()
        service = _patched_service(install, _status(install))
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=False),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle(force=True)
        assert data["upgraded"] is True

    def test_up_to_date_skips_upgrade(self) -> None:
        install = _install()
        service = _patched_service(
            install, _status(install, latest="1.4.2", update_available=False)
        )
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=True),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle()
        assert data["upgraded"] is False
        assert data["message"] == "Already up to date."
        service.upgrade.assert_not_called()

    def test_force_upgrades_even_when_up_to_date(self) -> None:
        install = _install()
        service = _patched_service(
            install, _status(install, latest="1.4.2", update_available=False)
        )
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=True),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle(force=True)
        assert data["upgraded"] is True
        service.upgrade.assert_called_once()

    def test_failed_upgrade_raises(self) -> None:
        install = _install()
        service = _patched_service(
            install,
            _status(install),
            UpgradeResult(success=False, message="Upgrade command failed."),
        )
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=True),
            pytest.raises(UsecliError, match="Upgrade command failed"),
        ):
            UpgradeCommand.__new__(UpgradeCommand).handle()

    @pytest.mark.parametrize(
        "overrides",
        [
            {"frozen": True, "pinned": True, "pinned_reason": "frozen bundle"},
            {
                "source": "git",
                "url": "https://github.com/foo/magic.git",
                "revision": "v1.2.0",
                "pinned": True,
                "pinned_reason": "Git tag (v1.2.0)",
            },
            {"source": "editable", "pinned": True, "pinned_reason": "editable install"},
            {"package": "", "source": "unknown", "installer": None},
        ],
    )
    def test_blocked_installs_never_mutate(self, overrides: dict[str, object]) -> None:
        install = _install(**overrides)
        service = _patched_service(install, _status(install))
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=True),
            pytest.raises(UsecliError),
        ):
            UpgradeCommand.__new__(UpgradeCommand).handle()
        service.upgrade.assert_not_called()


class TestHumanCheckOutput:
    def test_update_available_report(self) -> None:
        install = _install()
        service = _patched_service(install, _status(install))
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=False),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle(check=True)
        assert data["update_available"] is True
        service.upgrade.assert_not_called()

    def test_git_branch_report_shows_vcs_rows(self) -> None:
        install = _install(
            source="git",
            url="https://github.com/foo/magic.git",
            revision="main",
            commit="a" * 40,
        )
        service = _patched_service(
            install,
            UpgradeStatus(
                install=install,
                latest="b" * 40,
                update_available=True,
                detail="github.com/foo/magic",
            ),
        )
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=False),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle(check=True)
        assert data["source"] == "git"

    def test_pinned_tag_report(self) -> None:
        install = _install(
            source="git",
            url="https://github.com/foo/magic.git",
            revision="v1.2.0",
            commit=None,
            pinned=True,
            pinned_reason="Git tag (v1.2.0)",
        )
        service = _patched_service(
            install,
            UpgradeStatus(
                install=install,
                latest=None,
                update_available=False,
                detail="github.com/foo/magic",
            ),
        )
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=False),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle(check=True)
        assert data["pinned"] is True
        assert data["latest"] is None

    def test_up_to_date_report(self) -> None:
        install = _install()
        service = _patched_service(
            install, _status(install, latest="1.4.2", update_available=False)
        )
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            execution_context(json_mode=False),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle(check=True)
        assert data["update_available"] is False


class TestHumanApplyOutput:
    def test_confirm_yes_upgrades(self) -> None:
        install = _install()
        service = _patched_service(install, _status(install))
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.Confirm.ask",
                return_value=True,
            ) as confirm,
            execution_context(json_mode=False),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle()
        confirm.assert_called_once()
        assert data["upgraded"] is True

    def test_confirm_no_aborts(self) -> None:
        install = _install()
        service = _patched_service(install, _status(install))
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.Confirm.ask",
                return_value=False,
            ),
            execution_context(json_mode=False),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle()
        assert data["upgraded"] is False
        assert data["message"] == "Aborted."
        service.upgrade.assert_not_called()

    def test_up_to_date_message_without_prompt(self) -> None:
        install = _install()
        service = _patched_service(
            install, _status(install, latest="1.4.2", update_available=False)
        )
        with (
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.UpgradeService",
                service,
            ),
            patch(
                "usecli.cli.commands.defaults.base.upgrade_command.Confirm.ask"
            ) as confirm,
            execution_context(json_mode=False),
        ):
            data = UpgradeCommand.__new__(UpgradeCommand).handle()
        confirm.assert_not_called()
        assert data["message"] == "Already up to date."
        service.upgrade.assert_not_called()
