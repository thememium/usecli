"""Bundle and install Agent Skills with a usecli CLI.

A project ships a skill by placing a ``SKILL.md`` under its configured skills
directory (``paths.skills``, default ``skills`` next to
``usecli.config.toml``)::

    src/mycli/
        skills/
            deploy-checks/
                SKILL.md

A project CLI's ``skill:install`` discovers every skill under that directory
and installs it into each coding agent's own skills directory. It is only
exposed when the project has at least one bundled skill. The ``usecli``
framework binary instead installs its own generated ``usecli`` skill.
Installation is idempotent and user edits are preserved: an installed file
carries a marker with the hash of the content it was rendered from, so a later
release can update its own files without touching a file the user edited.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

SKILL_FILENAME = "SKILL.md"

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", re.DOTALL)
_SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_MARKER_RE = re.compile(r"\n?<!-- usecli-skill: name=(\S+) hash=([0-9a-f]{64}) -->\n?")


class SkillError(ValueError):
    """Raised when a bundled skill is malformed or a target is unknown."""


@dataclass(frozen=True)
class Skill:
    """One Agent Skill, ready to install."""

    name: str
    description: str
    content: str
    path: Path | None = None

    @property
    def source(self) -> str:
        return str(self.path) if self.path is not None else "generated"


@dataclass(frozen=True)
class AgentTarget:
    """Where one coding agent loads skills from.

    ``global_base`` and ``project_base`` are path templates without the
    ``/skills/<name>/SKILL.md`` suffix. ``env`` overrides the global base.
    """

    name: str
    global_base: str
    project_base: str
    env: str | None = None
    xdg_subdir: str | None = None

    def base(self, scope: str, *, project_root: Path) -> Path:
        """Return the agent's skills root for a project or global scope."""
        if scope == "global":
            return self._global_base()
        if scope == "project":
            return Path(self.project_base.format(project=project_root))
        raise ValueError(f"Unknown skill scope: {scope!r}")

    def resolve(self, scope: str, *, name: str, project_root: Path) -> Path:
        """Return the directory where one skill should be installed."""
        return self.base(scope, project_root=project_root) / "skills" / name

    def _global_base(self) -> Path:
        if self.env:
            raw = os.environ.get(self.env, "").strip()
            if raw:
                return Path(os.path.expanduser(raw))
        if self.xdg_subdir:
            raw = os.environ.get("XDG_CONFIG_HOME", "").strip()
            if raw:
                return Path(os.path.expanduser(raw)) / self.xdg_subdir
        return Path(self.global_base.format(home=Path.home()))


AGENT_TARGETS: dict[str, AgentTarget] = {
    "claude": AgentTarget(
        name="claude",
        global_base="{home}/.claude",
        project_base="{project}/.claude",
        env="CLAUDE_CONFIG_DIR",
    ),
    "opencode": AgentTarget(
        name="opencode",
        global_base="{home}/.config/opencode",
        project_base="{project}/.opencode",
        env="OPENCODE_CONFIG_DIR",
        xdg_subdir="opencode",
    ),
    "codex": AgentTarget(
        name="codex",
        global_base="{home}/.codex",
        project_base="{project}/.agents",
        env="CODEX_HOME",
    ),
    "pi": AgentTarget(
        name="pi",
        global_base="{home}/.pi/agent",
        project_base="{project}/.pi",
        env="PI_CODING_AGENT_DIR",
    ),
    "prime-agent": AgentTarget(
        name="prime-agent",
        global_base="{home}/.prime/agent",
        project_base="{project}/.prime",
        env="PRIME_AGENT_CODING_AGENT_DIR",
    ),
    "omp": AgentTarget(
        name="omp",
        global_base="{home}/.omp/agent",
        project_base="{project}/.omp",
        env="OMP_AGENT_DIR",
    ),
    "cursor": AgentTarget(
        name="cursor",
        global_base="{home}/.cursor",
        project_base="{project}/.cursor",
    ),
    "agents": AgentTarget(
        name="agents",
        global_base="{home}/.agents",
        project_base="{project}/.agents",
    ),
}

AGENT_ALIASES = {
    "claude-code": "claude",
    "prime": "prime-agent",
}

#: Common harnesses installed by default. ``--agent all`` selects the rest.
DEFAULT_AGENTS = ("claude", "codex", "cursor")


@dataclass(frozen=True)
class InstallResult:
    """One skill installed (or skipped) for one agent."""

    skill: str
    agent: str
    path: Path
    status: str


def _hash(content: str) -> str:
    return hashlib.sha256(content.rstrip("\n").encode()).hexdigest()


def _frontmatter_metadata(content: str) -> dict[str, str]:
    match = _FRONTMATTER_RE.match(content)
    if match is None:
        return {}

    metadata: dict[str, str] = {}
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        metadata[key] = value
    return metadata


def load_skill(path: str | Path) -> Skill:
    """Load and validate one ``SKILL.md``.

    Raises:
        SkillError: If the file is unreadable, lacks a valid ``name`` or
            ``description``, or uses a name outside the Agent Skills slug
            format.
    """
    skill_path = Path(path)
    try:
        content = skill_path.read_text(encoding="utf-8")
    except OSError as error:
        raise SkillError(f"Could not read skill {skill_path}: {error}") from error

    metadata = _frontmatter_metadata(content)
    name = metadata.get("name") or skill_path.parent.name
    description = metadata.get("description", "")

    if not name:
        raise SkillError(f"Skill {skill_path} has no name")
    if not _SKILL_NAME_RE.match(name):
        raise SkillError(
            f"Skill name {name!r} in {skill_path} must use lowercase letters, "
            "numbers, and hyphens"
        )
    if not description:
        raise SkillError(f"Skill {skill_path} has no description")

    return Skill(
        name=name,
        description=description,
        content=content,
        path=skill_path,
    )


def discover_skills(directory: str | Path) -> list[Skill]:
    """Find every valid skill under a directory (or load one SKILL.md file).

    Directories whose path parts start with ``.`` are ignored, so vendored
    checkouts and cache directories do not leak into the installed set.
    """
    root = Path(directory)
    if root.is_file():
        return [load_skill(root)]
    if not root.is_dir():
        return []

    skills: list[Skill] = []
    by_name: dict[str, Skill] = {}
    for skill_path in sorted(root.rglob(SKILL_FILENAME)):
        relative = skill_path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        skill = load_skill(skill_path)
        previous = by_name.get(skill.name)
        if previous is not None:
            raise SkillError(
                f"Duplicate skill name {skill.name!r}: {previous.path} and {skill.path}"
            )
        by_name[skill.name] = skill
        skills.append(skill)
    return skills


def resolve_agents(values: Iterable[str] | str | None) -> list[str]:
    """Expand agent names, aliases, comma-separated values, and ``all``."""
    if values is None:
        return list(DEFAULT_AGENTS)
    if isinstance(values, str):
        values = [values]
    else:
        values = list(values)
        if not values:
            return list(DEFAULT_AGENTS)

    selected: list[str] = []
    for raw in values:
        for part in raw.split(","):
            name = part.strip().lower()
            if not name:
                continue
            if name == "all":
                selected.extend(AGENT_TARGETS)
                continue
            name = AGENT_ALIASES.get(name, name)
            if name not in AGENT_TARGETS:
                choices = ", ".join(["all", *AGENT_TARGETS])
                raise SkillError(f"Unknown agent {name!r}. Choose one of: {choices}")
            selected.append(name)

    if not selected:
        raise SkillError("At least one agent is required")
    return list(dict.fromkeys(selected))


def select_skills(
    skills: Iterable[Skill], names: Iterable[str] | str | None
) -> list[Skill]:
    """Filter a skill set by name; unknown names are an error."""
    skill_list = list(skills)
    if names is None:
        return skill_list
    if isinstance(names, str):
        names = [names]

    requested: list[str] = []
    for raw in names:
        for part in raw.split(","):
            name = part.strip()
            if name:
                requested.append(name)
    if not requested:
        return skill_list

    by_name = {skill.name: skill for skill in skill_list}
    unknown = [name for name in requested if name not in by_name]
    if unknown:
        raise SkillError(f"Unknown skill(s): {', '.join(unknown)}")
    return list(dict.fromkeys(by_name[name] for name in requested))


def skill_markdown(skill: Skill) -> str:
    """Return the exact document written to disk for one skill."""
    body = skill.content.rstrip("\n")
    marker = f"<!-- usecli-skill: name={skill.name} hash={_hash(skill.content)} -->"
    return f"{body}\n\n{marker}\n"


def install_skill(
    skill: Skill,
    destination: str | Path,
    *,
    force: bool = False,
) -> str:
    """Install one skill at ``destination`` and return a status string.

    Statuses:
        ``installed``: the destination did not exist.
        ``already_installed``: the exact managed document is already present.
        ``updated``: an older managed document was upgraded.
        ``adopted``: an unmarked document already matched this skill.
        ``user_modified``: the existing document has user edits; left alone.
        ``overwritten``: user edits were replaced because ``force`` was set.
    """
    target = Path(destination)
    rendered = skill_markdown(skill)

    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rendered, encoding="utf-8")
        return "installed"

    existing = target.read_text(encoding="utf-8")
    if existing == rendered:
        return "already_installed"

    match = _MARKER_RE.search(existing)
    if match is not None:
        recorded_name, recorded_hash = match.groups()
        body = _MARKER_RE.sub("\n", existing).rstrip("\n")
        if recorded_name == skill.name and _hash(body) == recorded_hash:
            target.write_text(rendered, encoding="utf-8")
            return "updated"
        if force:
            target.write_text(rendered, encoding="utf-8")
            return "overwritten"
        return "user_modified"

    if existing.rstrip("\n") == skill.content.rstrip("\n"):
        target.write_text(rendered, encoding="utf-8")
        return "adopted"
    if force:
        target.write_text(rendered, encoding="utf-8")
        return "overwritten"
    return "user_modified"


def install_skills(
    skills: Iterable[Skill],
    *,
    agents: Iterable[str] | str | None = None,
    scope: str = "project",
    project_root: str | Path | None = None,
    force: bool = False,
) -> list[InstallResult]:
    """Install every skill into every selected agent target.

    Destinations are de-duplicated: ``codex`` and ``agents`` both resolve to
    the project's ``.agents/skills`` directory, so a skill is written once even
    when both targets are selected.
    """
    root = Path(project_root) if project_root is not None else Path.cwd()
    selected = resolve_agents(agents)
    results: list[InstallResult] = []
    seen: set[tuple[str, Path]] = set()

    for skill in skills:
        for agent in selected:
            destination = (
                AGENT_TARGETS[agent].resolve(
                    scope,
                    name=skill.name,
                    project_root=root,
                )
                / SKILL_FILENAME
            )
            key = (skill.name, destination)
            if key in seen:
                continue
            seen.add(key)

            try:
                status = install_skill(skill, destination, force=force)
            except OSError as error:
                status = f"error: {error}"
            results.append(
                InstallResult(
                    skill=skill.name,
                    agent=agent,
                    path=destination,
                    status=status,
                )
            )
    return results


__all__ = [
    "AGENT_ALIASES",
    "AGENT_TARGETS",
    "DEFAULT_AGENTS",
    "SKILL_FILENAME",
    "AgentTarget",
    "InstallResult",
    "Skill",
    "SkillError",
    "discover_skills",
    "install_skill",
    "install_skills",
    "load_skill",
    "resolve_agents",
    "select_skills",
    "skill_markdown",
]
