"""Persist upgraded versions into the owning project's dependency metadata.

An environment-level upgrade does not survive a dependency reinstall by
itself, so the upgrade is persisted into whichever metadata the project
actually uses:

- The running package IS the project (``project.name`` matches) → the
  version is rewritten in ``pyproject.toml``.
- The package is a git dependency of a uv project → the dependency's git
  ref is moved to the resolved release tag (in both the app's spec and the
  usecli framework's spec when the framework is a git dependency too) and
  ``uv.lock`` is refreshed with ``uv lock --upgrade-package``, so sync
  installs exactly the advertised release instead of reverting.
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

from usecli.shared.upgrades.discovery import InstallInfo

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


def _git_dependency(
    pyproject_path: Any,
    package: str,
) -> tuple[str, str, dict[str, Any] | None] | None:
    """Locate the git dependency declaring ``package``.

    Recognizes both forms uv writes: inline PEP 508 direct URLs in
    ``project.dependencies`` and ``[tool.uv.sources]`` git entries paired
    with a bare dependency name. Returns ``(form, value, entry)`` where
    form is ``"inline"`` (value = the spec string, entry = ``None``) or
    ``"sources"`` (value = the sources key, entry = the parsed entry), or
    ``None`` when the package has no git source.
    """
    try:
        with open(pyproject_path, "rb") as handle:
            data = _get_tomllib().load(handle)
    except (OSError, ValueError):
        return None
    target = _normalize_name(package)

    dependencies = data.get("project", {}).get("dependencies", [])
    if isinstance(dependencies, list):
        for spec in dependencies:
            if not isinstance(spec, str) or "git+" not in spec:
                continue
            match = re.match(r"\s*([A-Za-z0-9._-]+)", spec)
            if match is None:
                continue
            if _normalize_name(match.group(1)) == target:
                return ("inline", spec, None)

    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    if isinstance(sources, dict):
        for source_name, source_entry in sources.items():
            if (
                isinstance(source_entry, dict)
                and _normalize_name(str(source_name)) == target
                and isinstance(source_entry.get("git"), str)
            ):
                return ("sources", str(source_name), source_entry)
    return None


def _rewrite_git_pin(line: str, new_ref: str) -> tuple[str, str | None]:
    """Point a git requirement spec at ``new_ref``.

    Replaces an existing trailing ``@<rev>`` or appends one to the URL
    token. Anchored after the last path segment so ``ssh://git@host`` style
    URLs are not misread as pins; quote-aware so quoted TOML specs are
    handled. Returns ``(new_line, previous_revision)``.
    """
    git_pos = line.index("git+")
    pinned = re.search(r"@([A-Za-z0-9._-]+)(?=$|[\s#\"'])", line[git_pos:])
    if pinned is not None:
        start = git_pos + pinned.start(1)
        end = git_pos + pinned.end(1)
        return line[:start] + new_ref + line[end:], pinned.group(1)
    token_end = len(line)
    for position in range(git_pos, len(line)):
        if line[position] in " \t#\"'":
            token_end = position
            break
    return line[:token_end] + "@" + new_ref + line[token_end:], None


def _sources_entry_line(
    key: str,
    entry: dict[str, Any],
    tag: str | None,
) -> str:
    """Rebuild a ``[tool.uv.sources]`` inline-table entry pinned to ``tag``."""
    items = []
    for source_key, source_value in entry.items():
        if source_key in ("branch", "tag", "rev"):
            continue
        value = source_value if isinstance(source_value, str) else str(source_value)
        items.append(f'{source_key} = "{value}"')
    if tag:
        items.append(f'tag = "{tag}"')
    joined = ", ".join(items)
    return f"{key} = {{ {joined} }}"


def _rewrite_dependency_ref(
    lines: list[str],
    form: str,
    value: str,
    entry: dict[str, Any] | None,
    tag: str,
) -> bool:
    """Rewrite one dependency's git ref to ``tag`` in the pyproject lines.

    Returns True when a line changed.
    """
    if form == "inline":
        for index, line in enumerate(lines):
            if value in line and "git+" in line:
                new_line, _ = _rewrite_git_pin(line, tag)
                if new_line != line:
                    lines[index] = new_line
                    return True
                return False
        return False
    key_pattern = re.compile(rf"^\s*{re.escape(value)}\s*=")
    for index, line in enumerate(lines):
        if key_pattern.match(line):
            new_line = _sources_entry_line(value, entry or {}, tag)
            if new_line != line:
                lines[index] = new_line
                return True
            return False
    return False


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
    dependency: tuple[str, str, dict[str, Any] | None],
    install: InstallInfo,
    target_tag: str | None,
) -> PyprojectUpdate:
    """Persist a git-dependency upgrade.

    Moves the dependency's git ref to the resolved release tag (in the
    app's spec and in the usecli framework's spec when the framework is a
    git dependency of the same project) and refreshes ``uv.lock`` so
    ``uv sync`` installs exactly the advertised release instead of
    reverting to the stale pin.
    """
    import shutil
    import subprocess

    try:
        text = pyproject_path.read_text()
    except OSError:
        return PyprojectUpdate(
            path=str(pyproject_path),
            reason="could not read pyproject.toml",
        )

    framework = None
    if install.package != "usecli":
        framework = _git_dependency(pyproject_path, "usecli")

    lines = text.splitlines()
    rewritten = False
    if target_tag:
        form, value, entry = dependency
        rewritten = _rewrite_dependency_ref(lines, form, value, entry, target_tag)
        if framework is not None:
            framework_rewritten = _rewrite_dependency_ref(
                lines, framework[0], framework[1], framework[2], target_tag
            )
            rewritten = framework_rewritten or rewritten

    uv = shutil.which("uv")
    if uv is None:
        if rewritten:
            pyproject_path.write_text(text)
        return PyprojectUpdate(
            path=str(pyproject_path),
            reason="uv is required to refresh uv.lock",
        )

    if rewritten:
        try:
            pyproject_path.write_text(
                "\n".join(lines) + ("\n" if text.endswith("\n") else "")
            )
        except OSError:
            logger.debug("Failed to write pyproject.toml: %s", pyproject_path)
            return PyprojectUpdate(
                path=str(pyproject_path),
                reason="could not write pyproject.toml",
            )

    lock_command = [uv, "lock", "--upgrade-package", install.package]
    if framework is not None:
        lock_command += ["--upgrade-package", "usecli"]

    try:
        result = subprocess.run(
            lock_command,
            cwd=pyproject_path.parent,
            capture_output=True,
            text=True,
            check=False,
            timeout=_LOCK_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as error:
        logger.debug("uv lock failed: %s", error)
        if rewritten:
            pyproject_path.write_text(text)
        return PyprojectUpdate(
            path=str(pyproject_path),
            reason=f"uv lock failed: {error}",
        )

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()[-300:]
        if rewritten:
            pyproject_path.write_text(text)
        return PyprojectUpdate(
            path=str(pyproject_path),
            reason=f"uv lock failed: {detail}",
        )

    if target_tag:
        summary = (
            f"Pinned {install.package} to {target_tag} and refreshed uv.lock; "
            "uv sync will keep the upgrade."
        )
    else:
        summary = (
            f"Refreshed uv.lock for {install.package}; uv sync will keep the upgrade."
        )
    if framework is not None:
        summary = f"{summary} usecli refreshed alongside."
    return PyprojectUpdate(
        path=str(pyproject_path),
        new_version=_reinstalled_version(),
        updated=True,
        summary=summary,
    )


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


def persist_upgrade(
    install: InstallInfo,
    target_revision: str | None = None,
) -> PyprojectUpdate:
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
        dependency = _git_dependency(pyproject_path, install.package)
        if dependency is not None:
            return _persist_dependency(
                pyproject_path, dependency, install, target_revision
            )

    requirements_path = project_dir / "requirements.txt"
    if requirements_path.is_file():
        return _persist_requirements(requirements_path, install)

    return PyprojectUpdate(
        path=str(pyproject_path) if pyproject_path.is_file() else None,
        reason="package is not a dependency of this project",
    )
