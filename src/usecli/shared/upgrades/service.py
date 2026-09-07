"""Facade for the self-upgrade machinery.

Exposes the three-step API used by the built-in ``upgrade`` command:
discover how the app was installed, check for an update, apply the upgrade.
"""

from __future__ import annotations

from typing import Any

from usecli.shared.upgrades import checker, discovery, installer
from usecli.shared.upgrades.checker import UpgradeStatus
from usecli.shared.upgrades.discovery import InstallInfo
from usecli.shared.upgrades.installer import UpgradeResult


class UpgradeService:
    """High-level API for discovering, checking, and upgrading installs."""

    @staticmethod
    def discover(config: Any | None = None) -> InstallInfo:
        """Discover how the running application was installed."""
        return discovery.discover(config)

    @staticmethod
    def check(
        install: InstallInfo | None = None,
        config: Any | None = None,
    ) -> UpgradeStatus:
        """Check for an available update without mutating anything."""
        if install is None:
            install = discovery.discover(config)
        return checker.check(install)

    @staticmethod
    def upgrade(
        install: InstallInfo | None = None,
        config: Any | None = None,
        target_revision: str | None = None,
    ) -> UpgradeResult:
        """Apply an upgrade, installing ``target_revision`` for git sources."""
        if install is None:
            install = discovery.discover(config)
        return installer.upgrade(install, target_revision)


__all__ = ["UpgradeService"]
