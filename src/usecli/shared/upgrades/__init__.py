"""Reusable self-upgrade machinery for usecli applications.

Every generated CLI inherits a built-in ``upgrade`` command built on this
package. Installations are classified from standard packaging metadata
(``INSTALLER`` and PEP 610 ``direct_url.json``) — no CLI-author
configuration required.
"""

from usecli.shared.upgrades.checker import UpgradeStatus
from usecli.shared.upgrades.discovery import InstallInfo, InstallSource
from usecli.shared.upgrades.installer import UpgradeResult
from usecli.shared.upgrades.service import UpgradeService

__all__ = [
    "InstallInfo",
    "InstallSource",
    "UpgradeResult",
    "UpgradeService",
    "UpgradeStatus",
]
