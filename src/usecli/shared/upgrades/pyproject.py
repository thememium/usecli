"""Persist upgraded versions into the owning project's dependency metadata.

An environment-level upgrade does not survive a dependency reinstall by
itself, so the upgraded version is written back into whichever metadata the
project actually uses:

- The running package IS the project (``project.name`` matches) → the
  version is rewritten in ``pyproject.toml``.
- The package is a git dependency of a uv project → ``uv.lock`` is
  refreshed with ``uv lock --upgrade-package`` so sync keeps the upgrade.
- The project pins the package in ``requirements.txt`` → the git revision
  (or ``==`` version pin) is rewritten to what was installed.

All cases are located through the project venv layout (``<project>/.venv``);
global, user, uv tool, and pipx environments are left completely untouched.
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass
from typing import Any

from usecli.shared.upgrades.discovery import InstallInfo, _revision_kind

logger = logging.getLogger(__name__)

_LOCK_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class PyprojectUpdate:
    """Outcome of a dependency-metadata persistence attempt.

    Attributes:
        path: The metadata file that was considered (pyproject.toml or
            requirements.txt), when a project was detected.
        previous_version: Version or revision declared before the rewrite.
        new_version: Version or revision written (or attempted).
        updated: Whether persistence actually succeeded.
        reason: Why nothing changed, when ``updated`` is false.
        summary: Human-readable sentence describing the change.
    """

    path: str | None = None
    previous_version: str | None = None
    new_version: str | None = None
    updated: bool = False
    reason: str | None = None
    summary: str | None = None


def _get_path():
    from pathlib import Path

    return Path


def _get_tomllib():
    if sys.version_info >= (3, 11):
        import tomllib

        return tomllib
    import tomli as tomllib

    return tomllib


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).strip().lower()


def _read_project_name(pyproject_path: Any) -> str | None:
    try:
        with open(pyproject_path, "rb") as handle:
            data = _get_tomllib().load(handle)
    except (OSError, ValueError):
        return None
    name = data.get("project", {}).get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def _project_dir() -> Any | None:
    """Locate the project directory owning the running venv.

    Matches the project venv layout (``<project>/.venv`` or
    ``<project>/venv``) only; global, user, uv tool, and pipx environments
    have different prefixes and never match — so they are never modified.
    """
    prefix = _get_path()(sys.prefix)
    if prefix.name not in (".venv", "venv"):
        return None
    project_dir = prefix.parent
    if not project_dir.is_dir():
        return None
    return project_dir


def update_project_version(
    pyproject_path: Any,
    new_version: str,
) -> tuple[bool, str | None]:
    """Rewrite ``version`` inside the ``[project]`` table.

    Line-oriented edit: only the version value changes; comments, spacing,
    and every other line are preserved. Returns ``(changed,
    previous_version)`` and leaves the file untouched when the table has no
    static version or it already matches.
    """
    version_pattern = re.compile(
        r'^(?P<prefix>\s*version\s*=\s*["\'])(?P<value>[^"\']*)(?P<suffix>["\'].*)$'
    )
    try:
        text = pyproject_path.read_text()
    except OSError:
        return False, None

    lines = text.splitlines()
    in_project = False
    previous_version: str | None = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped == "[project]"
            continue
        if not in_project:
            continue
        match = version_pattern.match(line)
        if match is None:
            continue
        previous_version = match.group("value")
        if previous_version == new_version:
            return False, previous_version
        lines[index] = f"{match.group('prefix')}{new_version}{match.group('suffix')}"
        break
    else:
        return False, None

    trailing_newline = "\n" if text.endswith("\n") else ""
    try:
        pyproject_path.write_text("\n".join(lines) + trailing_newline)
    except OSError:
        logger.debug("Failed to write pyproject.toml: %s", pyproject_path)
        return False, previous_version
    return True, previous_version


def _dependency_git_spec(pyproject_path: Any, package: str) -> str | None:
    """Find the PEP 508 spec declaring ``package`` from a git source."""
    try:
        with open(pyproject_path, "rb") as handle:
            data = _get_tomllib().load(handle)
    except (OSError, ValueError):
        return None
    dependencies = data.get("project", {}).get("dependencies", [])
    if not isinstance(dependencies, list):
        return None
    for spec in dependencies:
        if not isinstance(spec, str) or "git+" not in spec:
            continue
        match = re.match(r"\s*([A-Za-z0-9._-]+)", spec)
        if match is None:
            continue
        if _normalize_name(match.group(1)) == _normalize_name(package):
            return spec
    return None


def _pinned_revision(spec_line: str) -> str | None:
    """Extract a static revision pin from a git dependency spec.

    Returns the pinned revision when the spec fixes a tag or commit (which
    ``uv lock --upgrade-package`` cannot move); ``None`` for unpinned or
    branch-pinned specs.
    """
    inline = re.search(r"git\+\S*?@([A-Za-z0-9._-]+)", spec_line)
    if inline is not None:
        return inline.group(1)
    sources = re.search(r'\brev\s*=\s*["\']([^"\']+)["\']', spec_line)
    if sources is not None:
        return sources.group(1)
    return None


def _refind_running_distribution() -> Any | None:
    """Re-read the running distribution after the environment changed."""
    from usecli.shared.config.manager import _reset_distributions_cache

    _reset_distributions_cache()

    from usecli.shared.upgrades.discovery import _find_running_distribution

    return _find_running_distribution()


def _reinstalled_version() -> str | None:
    dist = _refind_running_distribution()
    if dist is None:
        return None
    try:
        version = dist.version
    except (AttributeError, OSError, TypeError):
        return None
    return str(version) if version else None


def _reinstalled_commit() -> str | None:
    """Read the installed commit from the upgraded distribution's metadata."""
    import json

    dist = _refind_running_distribution()
    if dist is None:
        return None
    try:
        text = dist.read_text("direct_url.json")
    except (AttributeError, OSError, KeyError):
        return None
    if not text:
        return None
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    vcs_info = data.get("vcs_info")
    if not isinstance(vcs_info, dict):
        return None
    commit = vcs_info.get("commit_id")
    if isinstance(commit, str) and commit.strip():
        return commit.strip()
    return None


def _match_requirement(line: str, package: str) -> str | None:
    """Classify a requirements.txt line declaring ``package``.

    Returns ``"git"`` (direct URL or ``#egg=`` form), ``"pin"``
    (``name==version``), ``"url"`` (non-git direct URL), or ``None`` when
    the line does not declare the package.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    target = _normalize_name(package)
    candidates = (
        ("git", re.compile(r"^\s*(?:-e\s+)?git\+\S*#egg=([A-Za-z0-9._-]+)")),
        ("git", re.compile(r"^\s*(?:-e\s+)?([A-Za-z0-9._-]+)\s*@")),
        ("pin", re.compile(r"^\s*([A-Za-z0-9._-]+)\s*==")),
    )
    for kind, pattern in candidates:
        match = pattern.match(line)
        if match is None:
            continue
        if _normalize_name(match.group(1)) != target:
            return None
        if kind == "git" and "git+" not in line:
            return "url"
        return kind
    return None


def _rewrite_git_pin(line: str, new_commit: str) -> tuple[str, str | None]:
    """Point a git requirement line at ``new_commit``.

    Replaces an existing trailing ``@<rev>`` or appends one to the URL
    token. Anchored after the last path segment so ``ssh://git@host`` style
    URLs are not misread as pins. Returns ``(new_line, previous_revision)``.
    """
    git_pos = line.index("git+")
    pinned = re.search(r"@([A-Za-z0-9._-]+)(?=$|[\s#])", line[git_pos:])
    if pinned is not None:
        start = git_pos + pinned.start(1)
        end = git_pos + pinned.end(1)
        return line[:start] + new_commit + line[end:], pinned.group(1)
    token_end = len(line)
    for position in range(git_pos, len(line)):
        if line[position] in " \t#":
            token_end = position
            break
    return line[:token_end] + "@" + new_commit + line[token_end:], None


def _persist_self_version(pyproject_path: Any, install: InstallInfo) -> PyprojectUpdate:
    new_version = _reinstalled_version()
    if not new_version:
        return PyprojectUpdate(
            path=str(pyproject_path),
            reason="upgraded version could not be determined",
        )

    updated, previous_version = update_project_version(pyproject_path, new_version)
    if updated:
        reason = None
        summary = (
            f"Updated pyproject.toml version ({previous_version} → {new_version}); "
            "uv sync will keep it."
        )
    elif previous_version is None:
        reason = "no static version in [project]"
        summary = None
    else:
        reason = "version already matches"
        summary = None
    return PyprojectUpdate(
        path=str(pyproject_path),
        previous_version=previous_version,
        new_version=new_version,
        updated=updated,
        reason=reason,
        summary=summary,
    )


def _persist_dependency(
    pyproject_path: Any,
    spec: str,
    install: InstallInfo,
) -> PyprojectUpdate:
    import shutil
    import subprocess

    pin = _pinned_revision(spec)
    if pin is not None and _revision_kind(pin) in ("commit", "tag"):
        return PyprojectUpdate(
            path=str(pyproject_path),
            reason=(
                f"dependency pins revision '{pin}'; move the pin in "
                "pyproject.toml to upgrade"
            ),
        )

    uv = shutil.which("uv")
    if uv is None:
        return PyprojectUpdate(
            path=str(pyproject_path),
            reason="uv is required to refresh uv.lock",
        )

    try:
        result = subprocess.run(
            [uv, "lock", "--upgrade-package", install.package],
            cwd=pyproject_path.parent,
            capture_output=True,
            text=True,
            check=False,
            timeout=_LOCK_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as error:
        logger.debug("uv lock failed: %s", error)
        return PyprojectUpdate(
            path=str(pyproject_path),
            reason=f"uv lock failed: {error}",
        )

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()[-300:]
        return PyprojectUpdate(
            path=str(pyproject_path),
            reason=f"uv lock failed: {detail}",
        )

    return PyprojectUpdate(
        path=str(pyproject_path),
        new_version=_reinstalled_version(),
        updated=True,
        summary=(
            f"Refreshed uv.lock for {install.package}; uv sync will keep the upgrade."
        ),
    )


def _persist_requirements(
    requirements_path: Any,
    install: InstallInfo,
) -> PyprojectUpdate:
    """Rewrite the package's pin in requirements.txt to what was installed."""
    try:
        text = requirements_path.read_text()
    except OSError:
        return PyprojectUpdate(
            path=str(requirements_path),
            reason="could not read requirements.txt",
        )

    lines = text.splitlines()
    for index, line in enumerate(lines):
        kind = _match_requirement(line, install.package)
        if kind is None:
            continue
        if kind == "url":
            return PyprojectUpdate(
                path=str(requirements_path),
                reason="direct URL requirement; update requirements.txt manually",
            )
        if kind == "git":
            new_pin = _reinstalled_commit()
            if not new_pin:
                return PyprojectUpdate(
                    path=str(requirements_path),
                    reason="upgraded commit could not be determined",
                )
            new_line, previous_version = _rewrite_git_pin(line, new_pin)
            if new_line == line:
                return PyprojectUpdate(
                    path=str(requirements_path),
                    previous_version=previous_version,
                    new_version=new_pin,
                    reason="pin already matches",
                )
            lines[index] = new_line
            summary = (
                f"Pinned {install.package} to {new_pin[:12]} in "
                "requirements.txt; reinstalling keeps the upgrade."
            )
            new_version = new_pin
        else:
            pin_match = re.match(
                r"^(\s*[A-Za-z0-9._-]+\s*==\s*)([A-Za-z0-9.]+)(.*)$", line
            )
            assert pin_match is not None, "_match_requirement classified a pin"
            previous_version = pin_match.group(2)
            new_version = _reinstalled_version()
            if not new_version:
                return PyprojectUpdate(
                    path=str(requirements_path),
                    reason="upgraded version could not be determined",
                )
            if previous_version == new_version:
                return PyprojectUpdate(
                    path=str(requirements_path),
                    previous_version=previous_version,
                    new_version=new_version,
                    reason="version already matches",
                )
            new_line = f"{pin_match.group(1)}{new_version}{pin_match.group(3)}"
            lines[index] = new_line
            summary = (
                f"Updated requirements.txt pin for {install.package} "
                f"({previous_version} → {new_version}); reinstalling keeps "
                "the upgrade."
            )

        trailing_newline = "\n" if text.endswith("\n") else ""
        try:
            requirements_path.write_text("\n".join(lines) + trailing_newline)
        except OSError:
            logger.debug("Failed to write requirements.txt: %s", requirements_path)
            return PyprojectUpdate(
                path=str(requirements_path),
                previous_version=previous_version,
                new_version=new_version,
                reason="could not write requirements.txt",
            )
        return PyprojectUpdate(
            path=str(requirements_path),
            previous_version=previous_version,
            new_version=new_version,
            updated=True,
            summary=summary,
        )
    return PyprojectUpdate(
        path=str(requirements_path),
        reason="package not found in requirements.txt",
    )


def persist_upgrade(install: InstallInfo) -> PyprojectUpdate:
    """Persist the upgrade into the owning project's dependency metadata.

    Best-effort: every failure mode degrades to an explanatory
    :class:`PyprojectUpdate` instead of raising. Global, user, uv tool, and
    pipx installations are never paired with project metadata, so nothing
    is written for them.
    """
    project_dir = _project_dir()
    if project_dir is None:
        return PyprojectUpdate(reason="not a project-managed environment")

    pyproject_path = project_dir / "pyproject.toml"
    if pyproject_path.is_file():
        project_name = _read_project_name(pyproject_path)
        if project_name is not None and _normalize_name(
            project_name
        ) == _normalize_name(install.package):
            return _persist_self_version(pyproject_path, install)
        git_spec = _dependency_git_spec(pyproject_path, install.package)
        if git_spec is not None:
            return _persist_dependency(pyproject_path, git_spec, install)

    requirements_path = project_dir / "requirements.txt"
    if requirements_path.is_file():
        return _persist_requirements(requirements_path, install)

    return PyprojectUpdate(
        path=str(pyproject_path) if pyproject_path.is_file() else None,
        reason="package is not a dependency of this project",
    )
