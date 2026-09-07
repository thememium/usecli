"""Tests for the UpgradeService facade."""

from __future__ import annotations

from unittest.mock import Mock, patch

from usecli.shared.upgrades import UpgradeService
from usecli.shared.upgrades.discovery import InstallInfo


def _install() -> InstallInfo:
    return InstallInfo(package="magic-cli", version="1.4.2", source="index")


class TestDiscover:
    def test_forwards_config(self) -> None:
        config = object()
        with patch(
            "usecli.shared.upgrades.discovery.discover", return_value="info"
        ) as discover:
            result = UpgradeService.discover(config)
        discover.assert_called_once_with(config)
        assert result == "info"


class TestCheck:
    def test_discovers_when_install_omitted(self) -> None:
        install = _install()
        status = Mock()
        with (
            patch(
                "usecli.shared.upgrades.discovery.discover",
                return_value=install,
            ) as discover,
            patch("usecli.shared.upgrades.checker.check", return_value=status) as check,
        ):
            result = UpgradeService.check(config="cfg")
        discover.assert_called_once_with("cfg")
        check.assert_called_once_with(install)
        assert result is status

    def test_uses_provided_install(self) -> None:
        install = _install()
        with (
            patch("usecli.shared.upgrades.discovery.discover") as discover,
            patch(
                "usecli.shared.upgrades.checker.check", return_value="status"
            ) as check,
        ):
            result = UpgradeService.check(install)
        discover.assert_not_called()
        check.assert_called_once_with(install)
        assert result == "status"


class TestUpgrade:
    def test_discovers_when_install_omitted(self) -> None:
        install = _install()
        result = Mock()
        with (
            patch(
                "usecli.shared.upgrades.discovery.discover",
                return_value=install,
            ) as discover,
            patch(
                "usecli.shared.upgrades.installer.upgrade", return_value=result
            ) as upgrade,
        ):
            outcome = UpgradeService.upgrade(config="cfg")
        discover.assert_called_once_with("cfg")
        upgrade.assert_called_once_with(install, None)
        assert outcome is result

    def test_uses_provided_install(self) -> None:
        install = _install()
        with (
            patch("usecli.shared.upgrades.discovery.discover") as discover,
            patch(
                "usecli.shared.upgrades.installer.upgrade", return_value="result"
            ) as upgrade,
        ):
            outcome = UpgradeService.upgrade(install, target_revision="v0.1.4")
        discover.assert_not_called()
        upgrade.assert_called_once_with(install, "v0.1.4")
        assert outcome == "result"
