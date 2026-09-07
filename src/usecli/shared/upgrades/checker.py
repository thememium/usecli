"""Check whether a newer version of the running application is available.

Checking never mutates anything: index installs are compared against the
PyPI JSON API, and Git branch installs are compared against the remote
branch head. Pinned installations (tags, commits, direct URLs, editable
installs) report no remote check at all.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from usecli.shared.upgrades.discovery import InstallInfo

logger = logging.getLogger(__name__)

_PYPI_TIMEOUT_SECONDS = 10
_GIT_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class UpgradeStatus:
    """Result of a non-mutating upgrade check.

    Attributes:
        install: The installation that was checked.
        latest: Latest available version (index installs) or commit id
            (Git branch installs). ``None`` when unavailable.
        update_available: Whether an update was found.
        detail: Human-readable source label (e.g. ``PyPI``).
        error: Description of why the check could not run, if it failed.
    """

    install: InstallInfo
    latest: str | None = None
    update_available: bool = False
    detail: str | None = None
    error: str | None = None


def _normalize_pypi_name(name: str) -> str:
    """Normalize a package name per PEP 503 for PyPI URL construction."""
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def _parse_version(version: str) -> tuple[int, ...] | None:
    """Parse the leading numeric components of a version string.

    Returns None when the version has no numeric prefix (e.g. a bare commit
    id), in which case callers fall back to inequality comparison.
    """
    match = re.match(r"\s*v?(\d+(?:\.\d+)*)", version)
    if not match:
        return None
    return tuple(int(part) for part in match.group(1).split("."))


def _version_is_newer(latest: str, current: str) -> bool:
    """Return whether ``latest`` is a newer release than ``current``.

    When either version cannot be parsed numerically, any difference is
    treated as an available update.
    """
    latest_parsed = _parse_version(latest)
    current_parsed = _parse_version(current)
    if latest_parsed is None or current_parsed is None:
        return latest.strip() != current.strip()
    return latest_parsed > current_parsed


def _display_url(url: str) -> str:
    """Render a repository URL for display (no scheme, no .git suffix)."""
    display = re.sub(r"^[a-zA-Z][\w+.-]*://", "", url)
    if "@" in display:
        display = display.replace(":", "/", 1)
        display = display.split("@", 1)[1]
    return display.removesuffix(".git")


def source_detail(install: InstallInfo) -> str:
    """Return a human-readable label for the installation source."""
    if install.source == "index":
        return "PyPI"
    if install.source in ("git", "url") and install.url:
        return _display_url(install.url)
    if install.source == "editable":
        return "editable install"
    return install.source


def _fetch_pypi_latest(package: str) -> str | None:
    """Fetch the latest released version of ``package`` from PyPI.

    Raises:
        OSError: On network failures (``urllib.error.URLError`` subclasses
            ``OSError``).
        ValueError: On malformed responses.
    """
    import json
    import urllib.request

    normalized = _normalize_pypi_name(package)
    url = f"https://pypi.org/pypi/{normalized}/json"
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "usecli-upgrade"},
    )
    with urllib.request.urlopen(request, timeout=_PYPI_TIMEOUT_SECONDS) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise TypeError("Unexpected PyPI response format")
    version = data.get("info", {}).get("version")
    if isinstance(version, str) and version.strip():
        return version.strip()
    return None


def _fetch_git_head(url: str, revision: str | None) -> str | None:
    """Fetch the current commit id of a remote branch via ``git ls-remote``.

    No clone is performed. When ``revision`` is None the remote HEAD is
    queried instead. Raises ``OSError``/``subprocess.SubprocessError`` on
    failure; returns None when the ref does not exist.
    """
    import subprocess

    ref = f"refs/heads/{revision}" if revision else "HEAD"
    result = subprocess.run(
        ["git", "ls-remote", url, ref],
        capture_output=True,
        text=True,
        check=False,
        timeout=_GIT_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        logger.debug("git ls-remote failed: %s", result.stderr.strip())
        return None
    for line in result.stdout.splitlines():
        sha = line.split("\t", 1)[0].strip()
        if sha:
            return sha
    return None


def check(install: InstallInfo) -> UpgradeStatus:
    """Check the running installation for an available update.

    Args:
        install: The installation to check (see ``discovery.discover``).

    Returns:
        An :class:`UpgradeStatus` describing whether an update exists.
        Pinned installations never contact the network.
    """
    detail = source_detail(install)

    if install.frozen:
        return UpgradeStatus(
            install=install,
            detail=detail,
            error="Running from a frozen bundle; version checks are unavailable.",
        )

    if install.source == "unknown":
        return UpgradeStatus(
            install=install,
            detail=detail,
            error=(
                "Could not determine how this application was installed; "
                "checking for updates is unavailable."
            ),
        )

    # Pinned sources (tags, SHAs, direct URLs, editable installs) never
    # auto-upgrade, so no remote check is performed.
    if install.pinned or install.source in ("editable", "url"):
        return UpgradeStatus(install=install, detail=detail)

    if install.source == "index":
        try:
            latest = _fetch_pypi_latest(install.package)
        except (OSError, ValueError, TypeError) as error:
            logger.debug("PyPI check failed: %s", error)
            return UpgradeStatus(
                install=install,
                detail=detail,
                error=f"Could not reach PyPI: {error}",
            )
        if not latest:
            return UpgradeStatus(
                install=install,
                detail=detail,
                error=(
                    f"No release information found on PyPI for '{install.package}'."
                ),
            )
        return UpgradeStatus(
            install=install,
            latest=latest,
            update_available=_version_is_newer(latest, install.version),
            detail=detail,
        )

    if install.source == "git":
        import subprocess

        if not install.url:
            return UpgradeStatus(
                install=install,
                detail=detail,
                error="The installation record does not include a Git URL.",
            )
        try:
            latest = _fetch_git_head(install.url, install.revision)
        except (OSError, subprocess.SubprocessError) as error:
            logger.debug("git ls-remote failed: %s", error)
            return UpgradeStatus(
                install=install,
                detail=detail,
                error=f"Could not query the remote Git repository: {error}",
            )
        if not latest:
            return UpgradeStatus(
                install=install,
                detail=detail,
                error=(
                    f"Could not resolve remote branch '{install.revision or 'HEAD'}'."
                ),
            )
        return UpgradeStatus(
            install=install,
            latest=latest,
            update_available=bool(install.commit and latest != install.commit),
            detail=detail,
        )

    return UpgradeStatus(
        install=install,
        detail=detail,
        error=f"Unsupported installation source: {install.source}.",
    )


__all__ = ["UpgradeStatus", "check", "source_detail"]
