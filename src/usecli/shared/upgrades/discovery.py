"""Discover how the running CLI application was installed.

Builds an :class:`InstallInfo` record for the distribution that owns the
currently running console script, using standard Python packaging metadata:
the ``INSTALLER`` file and the PEP 610 ``direct_url.json`` metadata file.
This lets a generated CLI offer a self-upgrade command without the CLI
author having to declare how the app was distributed.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Literal

from usecli.shared.config.manager import _find_distribution_for_console_script

logger = logging.getLogger(__name__)

InstallSource = Literal["index", "git", "url", "editable", "unknown"]


@dataclass(frozen=True)
class InstallInfo:
    """How the currently running application was installed.

    Attributes:
        package: Installed distribution name (e.g. ``magic-cli``).
        version: Installed version string.
        source: Install classification derived from packaging metadata.
        installer: Content of the ``INSTALLER`` file (e.g. ``uv``, ``pip``).
        url: Direct URL the distribution was installed from, when recorded.
        revision: Requested VCS revision (branch, tag, or commit) for Git
            installs, when recorded.
        commit: Installed VCS commit id for Git installs, when recorded.
        pinned: Whether the installation is fixed and must not auto-upgrade
            (commit SHAs, direct URLs, editable installs, bundles). Branch
            and tag revisions track releases and are not pinned.
        pinned_reason: Human-readable explanation when ``pinned`` is true.
        frozen: Whether the app runs from a frozen bundle (e.g. PyInstaller).
    """

    package: str
    version: str
    source: InstallSource = "unknown"
    installer: str | None = None
    url: str | None = None
    revision: str | None = None
    commit: str | None = None
    pinned: bool = False
    pinned_reason: str | None = None
    frozen: bool = False


def _running_command_name() -> str | None:
    """Return the console-script name the app was invoked as."""
    return os.path.basename(sys.argv[0]) if sys.argv else None


def _find_running_distribution() -> Any | None:
    """Find the distribution that owns the currently running console script.

    Mirrors the resolution order used by the ``about`` command: look up the
    invoked script name first, then the configured primary command name.
    """
    command_name = _running_command_name()
    if command_name:
        dist = _find_distribution_for_console_script(command_name)
        if dist is not None:
            return dist
    from usecli.cli.core.ui.title import get_script_command_name

    primary_command = get_script_command_name(default=None)
    if primary_command and primary_command != command_name:
        return _find_distribution_for_console_script(primary_command)
    return None


def _read_dist_text(dist: Any, name: str) -> str | None:
    """Read a metadata file from a distribution, returning None on failure."""
    try:
        text = dist.read_text(name)
    except (AttributeError, OSError, KeyError):
        return None
    return text if isinstance(text, str) else None


def _dist_name(dist: Any) -> str:
    """Extract the distribution name from its package metadata."""
    metadata = getattr(dist, "metadata", None)
    if metadata is None:
        return ""
    try:
        name = metadata.get("Name") or metadata.get("name") or ""
    except (AttributeError, TypeError):
        return ""
    return str(name).strip()


def _dist_version(dist: Any, config: Any | None) -> str:
    """Resolve the installed version, with config/metadata fallbacks."""
    try:
        version = dist.version
        if version:
            return str(version)
    except (AttributeError, OSError, TypeError):
        logger.debug("Failed to read version from distribution metadata")
    return _fallback_version(config)


def _fallback_version(config: Any | None) -> str:
    """Best-effort version when no distribution could be identified."""
    if config is None:
        try:
            from usecli.shared.config.manager import get_config

            config = get_config()
        except (ImportError, OSError):
            config = None
    if config is not None:
        try:
            version = config.get_project_version()
            if version:
                return str(version)
        except (AttributeError, OSError, ValueError):
            logger.debug("Failed to read project version from pyproject.toml")
    try:
        from importlib.metadata import version as get_version

        return get_version("usecli")
    except (OSError, ValueError):
        return "0.0.0"


def _parse_direct_url(text: str | None) -> dict[str, Any] | None:
    """Parse a PEP 610 ``direct_url.json`` payload."""
    if not text:
        return None
    import json

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _revision_kind(revision: str | None) -> Literal["commit", "tag", "branch"] | None:
    """Classify a requested VCS revision.

    Heuristic, no network required:

    - 7-40 hex characters → a commit SHA.
    - ``v?1``, ``v1.2``, ``1.2.3`` style values → a version tag.
    - Anything else (``main``, ``develop``, ...) → a branch.
    """
    if not revision:
        return None
    stripped = revision.strip()
    if not stripped:
        return None
    import re

    if re.fullmatch(r"[0-9a-fA-F]{7,40}", stripped):
        return "commit"
    if re.fullmatch(r"v?\d+(\.\d+){0,3}", stripped):
        return "tag"
    return "branch"


def discover(config: Any | None = None) -> InstallInfo:
    """Build an :class:`InstallInfo` for the running application.

    Args:
        config: Optional ConfigManager used for the version fallback when no
            distribution can be identified. Defaults to the global config.

    Returns:
        The discovered installation details. ``source`` is ``"unknown"`` and
        ``pinned`` is true when the installation cannot be classified (frozen
        bundles, unidentified distributions).
    """
    if getattr(sys, "frozen", False):
        return InstallInfo(
            package=_running_command_name() or "application",
            version=_fallback_version(config),
            source="unknown",
            pinned=True,
            pinned_reason="frozen bundle",
            frozen=True,
        )

    dist = _find_running_distribution()
    if dist is None:
        logger.debug("No distribution found for the running console script")
        return InstallInfo(
            package=_running_command_name() or "application",
            version=_fallback_version(config),
            source="unknown",
            pinned=True,
            pinned_reason="installation source could not be determined",
        )

    package = _dist_name(dist)
    version = _dist_version(dist, config)

    installer_text = _read_dist_text(dist, "INSTALLER")
    installer = installer_text.strip().lower() if installer_text else None

    direct_url = _parse_direct_url(_read_dist_text(dist, "direct_url.json"))

    if direct_url is None:
        return InstallInfo(
            package=package,
            version=version,
            source="index",
            installer=installer,
        )

    dir_info = direct_url.get("dir_info")
    if isinstance(dir_info, dict) and dir_info.get("editable") is True:
        return InstallInfo(
            package=package,
            version=version,
            source="editable",
            installer=installer,
            url=direct_url.get("url") or None,
            pinned=True,
            pinned_reason="editable install",
        )

    vcs_info = direct_url.get("vcs_info")
    if isinstance(vcs_info, dict):
        vcs = vcs_info.get("vcs")
        url = direct_url.get("url") or None
        revision = vcs_info.get("requested_revision") or None
        commit = vcs_info.get("commit_id") or None
        if vcs and vcs != "git":
            return InstallInfo(
                package=package,
                version=version,
                source="url",
                installer=installer,
                url=url,
                revision=revision,
                commit=commit,
                pinned=True,
                pinned_reason=f"{vcs} VCS install",
            )
        kind = _revision_kind(revision)
        if kind == "commit":
            return InstallInfo(
                package=package,
                version=version,
                source="git",
                installer=installer,
                url=url,
                revision=revision,
                commit=commit,
                pinned=True,
                pinned_reason=f"Git commit ({revision})",
            )
        # Branch and tag revisions both track releases: branch installs
        # upgrade to the latest tag, and tag installs upgrade to the next
        # one — so neither is pinned.
        return InstallInfo(
            package=package,
            version=version,
            source="git",
            installer=installer,
            url=url,
            revision=revision,
            commit=commit,
        )

    url = direct_url.get("url") or None
    return InstallInfo(
        package=package,
        version=version,
        source="url",
        installer=installer,
        url=url,
        pinned=True,
        pinned_reason="direct URL install",
    )
