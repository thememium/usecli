"""Apply an upgrade to the running application's installation.

The installer prioritizes the package manager that originally installed the
distribution (recorded in the ``INSTALLER`` metadata file), falling back to
whatever tooling is available on the current machine:

1. ``uv tool`` environments → ``uv tool upgrade`` (index) or a forced
   reinstall from the original Git source (branch installs).
2. Other uv-managed environments → ``uv pip install --python <current>``.
3. pipx environments → ``pipx upgrade``.
4. Everything else → ``<current python> -m pip install --upgrade``.

Pinned, editable, and frozen installations are never mutated.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass

from usecli.shared.upgrades.discovery import InstallInfo

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UpgradeResult:
    """Outcome of an upgrade attempt.

    Attributes:
        success: Whether the upgrade command completed successfully.
        command: The exact command that was run, when a mutation was tried.
        message: Additional failure detail, when the upgrade did not run or
            failed.
    """

    success: bool
    command: tuple[str, ...] | None = None
    message: str | None = None


def _shutil_which(name: str) -> str | None:
    """Locate an executable on PATH (thin wrapper to ease testing)."""
    import shutil

    return shutil.which(name)


def _get_path():
    from pathlib import Path

    return Path


def _is_uv_tool_environment() -> bool:
    """Whether the current interpreter lives in a ``uv tool`` environment.

    uv tool environments live under ``.../uv/tools/<name>/`` on every
    platform, so checking path components avoids shelling out to
    ``uv tool dir``.
    """
    parts = _get_path()(sys.executable).parts
    return "uv" in parts and "tools" in parts


def _is_pipx_environment() -> bool:
    """Whether the current interpreter lives in a pipx-managed venv."""
    parts = _get_path()(sys.executable).parts
    return "pipx" in parts


def _pip_target(install: InstallInfo) -> str:
    """Build the PEP 508 target for pip-style installers.

    Git branch installs are reinstalled from the original URL and revision
    so the upgrade re-resolves the branch head; index installs upgrade to
    the latest compatible release.
    """
    if install.source == "git" and install.url:
        target = f"{install.package} @ git+{install.url}"
        if install.revision:
            target = f"{target}@{install.revision}"
        return target
    return install.package


def _run(command: list[str]) -> UpgradeResult:
    """Execute an upgrade command, capturing failure detail."""
    import shlex
    import subprocess

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        logger.debug("Failed to run upgrade command: %s", error)
        return UpgradeResult(
            success=False,
            command=tuple(command),
            message=f"Failed to run '{command[0]}': {error}",
        )

    if result.returncode == 0:
        return UpgradeResult(success=True, command=tuple(command))

    detail = (result.stderr or result.stdout or "").strip()
    if len(detail) > 400:
        detail = detail[-400:]
    message = f"Upgrade command failed with exit code {result.returncode}."
    if detail:
        message = f"{message}\n{detail}"
    message = f"{message}\nRun manually: {shlex.join(command)}"
    return UpgradeResult(
        success=False,
        command=tuple(command),
        message=message,
    )


def upgrade(install: InstallInfo) -> UpgradeResult:
    """Upgrade the running installation.

    Args:
        install: The installation to upgrade (see ``discovery.discover``).

    Returns:
        An :class:`UpgradeResult`. Installations that must not be mutated
        (frozen bundles, editable installs, pinned sources) return a failure
        result with an explanatory message instead of raising.
    """
    if install.frozen:
        return UpgradeResult(
            success=False,
            message=(
                "This application runs from a frozen bundle and cannot "
                "self-upgrade. Rebuild or download a new release."
            ),
        )

    if install.source == "editable":
        return UpgradeResult(
            success=False,
            message=(
                "This is an editable install; update the source repository "
                "and re-sync (e.g. `uv sync`) instead."
            ),
        )

    if install.pinned:
        return UpgradeResult(
            success=False,
            message=(
                f"This installation is pinned ({install.pinned_reason}) and "
                "will not automatically upgrade. Reinstall from the source "
                "you want to move to."
            ),
        )

    if not install.package or install.source == "unknown":
        return UpgradeResult(
            success=False,
            message=(
                "Could not determine how this application was installed; "
                "automatic upgrade is unavailable."
            ),
        )

    installer = install.installer or ""
    target = _pip_target(install)

    if installer == "uv" or _is_uv_tool_environment():
        uv = _shutil_which("uv")
        if uv is None and _is_uv_tool_environment():
            return UpgradeResult(
                success=False,
                message=(
                    "uv is required to upgrade this installation. Install "
                    "it from https://docs.astral.sh/uv/."
                ),
            )
        if uv is not None:
            if _is_uv_tool_environment():
                if install.source == "git":
                    # Reinstall from the original source so uv re-resolves
                    # the requested branch head. `uv tool upgrade` retains
                    # the original settings for registry installs.
                    command = [uv, "tool", "install", "--force", target]
                else:
                    command = [uv, "tool", "upgrade", install.package]
            else:
                command = [
                    uv,
                    "pip",
                    "install",
                    "--python",
                    sys.executable,
                    "--upgrade",
                    target,
                ]
            return _run(command)
        # uv binary missing but not a tool environment: fall through to pip.

    if installer == "pipx" or _is_pipx_environment():
        pipx = _shutil_which("pipx")
        if pipx is None:
            return UpgradeResult(
                success=False,
                message=(
                    "pipx is required to upgrade this installation. Run "
                    f"manually: pipx upgrade {install.package}"
                ),
            )
        return _run([pipx, "upgrade", install.package])

    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        target,
    ]
    return _run(command)


__all__ = ["UpgradeResult", "upgrade"]
