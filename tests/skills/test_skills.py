"""Tests for usecli.skills."""

from __future__ import annotations

from pathlib import Path

import pytest

from usecli.skills import (
    AGENT_TARGETS,
    DEFAULT_AGENTS,
    AgentTarget,
    Skill,
    SkillError,
    discover_skills,
    install_skill,
    install_skills,
    load_skill,
    resolve_agents,
    select_skills,
    skill_markdown,
)


def _content(
    name: str = "demo",
    *,
    description: str = "A demo skill",
    body: str = "# Demo\n",
) -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\n{body}"


def _skill(
    name: str = "demo",
    *,
    description: str = "A demo skill",
    body: str = "# Demo\n",
) -> Skill:
    return Skill(
        name=name,
        description=description,
        content=_content(name, description=description, body=body),
    )


def _write_skill(root: Path, name: str = "demo", **kwargs) -> Path:
    path = root / name / "SKILL.md"
    path.parent.mkdir(parents=True)
    path.write_text(_content(name, **kwargs), encoding="utf-8")
    return path


class TestLoadSkill:
    def test_parses_frontmatter(self, tmp_path: Path) -> None:
        path = _write_skill(tmp_path, "my-skill", description='"A: quoted skill"')

        skill = load_skill(path)

        assert skill.name == "my-skill"
        assert skill.description == "A: quoted skill"
        assert skill.path == path
        assert skill.source == str(path)

    def test_skips_comments_and_lines_without_colons(self, tmp_path: Path) -> None:
        path = tmp_path / "SKILL.md"
        path.write_text(
            "---\n# comment\nname: demo\nnot a field\n\n"
            "description: Demo\n---\n\nbody\n",
            encoding="utf-8",
        )

        skill = load_skill(path)

        assert skill.name == "demo"
        assert skill.description == "Demo"

    def test_name_falls_back_to_parent_directory(self, tmp_path: Path) -> None:
        path = tmp_path / "fallback" / "SKILL.md"
        path.parent.mkdir()
        path.write_text("---\ndescription: Demo\n---\nbody\n", encoding="utf-8")

        assert load_skill(path).name == "fallback"

    def test_missing_name_and_parent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        Path("SKILL.md").write_text(
            "---\ndescription: Demo\n---\nbody\n", encoding="utf-8"
        )

        with pytest.raises(SkillError, match="has no name"):
            load_skill(Path("SKILL.md"))

    def test_rejects_invalid_name(self, tmp_path: Path) -> None:
        path = _write_skill(tmp_path, "Valid Name")

        with pytest.raises(SkillError, match="lowercase letters"):
            load_skill(path)

    def test_rejects_missing_description(self, tmp_path: Path) -> None:
        path = tmp_path / "demo" / "SKILL.md"
        path.parent.mkdir()
        path.write_text("---\nname: demo\n---\nbody\n", encoding="utf-8")

        with pytest.raises(SkillError, match="has no description"):
            load_skill(path)

    def test_reports_unreadable_file(self, tmp_path: Path) -> None:
        with pytest.raises(SkillError, match="Could not read skill"):
            load_skill(tmp_path / "missing" / "SKILL.md")

    def test_missing_frontmatter_is_missing_description(self, tmp_path: Path) -> None:
        path = tmp_path / "demo" / "SKILL.md"
        path.parent.mkdir()
        path.write_text("# no frontmatter\n", encoding="utf-8")

        with pytest.raises(SkillError, match="has no description"):
            load_skill(path)


class TestDiscoverSkills:
    def test_missing_directory_is_empty(self, tmp_path: Path) -> None:
        assert discover_skills(tmp_path / "missing") == []

    def test_loads_a_file_directly(self, tmp_path: Path) -> None:
        path = _write_skill(tmp_path, "demo")
        assert [skill.name for skill in discover_skills(path)] == ["demo"]

    def test_discovers_nested_skills_and_skips_hidden(self, tmp_path: Path) -> None:
        _write_skill(tmp_path, "first")
        _write_skill(tmp_path / "nested", "second")
        _write_skill(tmp_path / ".hidden", "hidden")

        assert [skill.name for skill in discover_skills(tmp_path)] == [
            "first",
            "second",
        ]

    def test_rejects_duplicate_names(self, tmp_path: Path) -> None:
        _write_skill(tmp_path / "one", "demo")
        _write_skill(tmp_path / "two", "demo")

        with pytest.raises(SkillError, match="Duplicate skill name"):
            discover_skills(tmp_path)


class TestResolveAgents:
    def test_defaults(self) -> None:
        assert resolve_agents(None) == list(DEFAULT_AGENTS)
        assert resolve_agents([]) == list(DEFAULT_AGENTS)

    def test_string_and_all(self) -> None:
        assert resolve_agents("claude") == ["claude"]
        assert resolve_agents("all") == list(AGENT_TARGETS)

    def test_aliases_commas_and_deduplication(self) -> None:
        assert resolve_agents(["claude-code", "agents,claude-code"]) == [
            "claude",
            "agents",
        ]

    def test_unknown_agent(self) -> None:
        with pytest.raises(SkillError, match="Unknown agent"):
            resolve_agents(["unknown"])

    def test_empty_selection(self) -> None:
        with pytest.raises(SkillError, match="At least one agent"):
            resolve_agents([" , "])


class TestSelectSkills:
    def test_none_selects_everything(self) -> None:
        skills = [_skill("one"), _skill("two")]
        assert select_skills(skills, None) == skills

    def test_filters_by_string_list_and_empty(self) -> None:
        one = _skill("one")
        two = _skill("two")
        skills = [one, two]

        assert select_skills(skills, "one") == [one]
        assert select_skills(skills, ["one,two", "one"]) == [one, two]
        assert select_skills(skills, " , ") == skills

    def test_unknown_name(self) -> None:
        with pytest.raises(SkillError, match="Unknown skill"):
            select_skills([_skill("one")], ["missing"])


class TestAgentTarget:
    def test_project_and_global_paths(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
        target = AGENT_TARGETS["claude"]

        assert target.base("project", project_root=tmp_path) == (tmp_path / ".claude")
        assert target.base("global", project_root=tmp_path) == (
            tmp_path / "home" / ".claude"
        )
        assert target.resolve("project", name="demo", project_root=tmp_path) == (
            tmp_path / ".claude" / "skills" / "demo"
        )

    def test_environment_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "custom"))

        assert AGENT_TARGETS["claude"].base("global", project_root=tmp_path) == (
            tmp_path / "custom"
        )

    def test_xdg_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENCODE_CONFIG_DIR", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))

        assert AGENT_TARGETS["opencode"].base("global", project_root=tmp_path) == (
            tmp_path / "xdg" / "opencode"
        )

    def test_opencode_env_override(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("OPENCODE_CONFIG_DIR", str(tmp_path / "opencode"))

        assert AGENT_TARGETS["opencode"].base("global", project_root=tmp_path) == (
            tmp_path / "opencode"
        )

    def test_unknown_scope(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unknown skill scope"):
            AGENT_TARGETS["claude"].base("elsewhere", project_root=tmp_path)

    def test_custom_target(self, tmp_path: Path) -> None:
        target = AgentTarget(
            name="custom",
            global_base="{home}/.custom",
            project_base="{project}/.custom",
        )
        assert target.base("project", project_root=tmp_path) == (tmp_path / ".custom")


class TestMarker:
    def test_skill_markdown_appends_a_marker(self) -> None:
        skill = _skill()

        rendered = skill_markdown(skill)

        assert rendered.startswith(skill.content.rstrip("\n"))
        assert "<!-- usecli-skill: name=demo hash=" in rendered


class TestInstallSkill:
    def test_installs_with_parents(self, tmp_path: Path) -> None:
        target = tmp_path / "nested" / "SKILL.md"
        skill = _skill()

        assert install_skill(skill, target) == "installed"
        assert "usecli-skill" in target.read_text(encoding="utf-8")

    def test_exact_install_is_idempotent(self, tmp_path: Path) -> None:
        target = tmp_path / "SKILL.md"
        skill = _skill()
        install_skill(skill, target)

        assert install_skill(skill, target) == "already_installed"

    def test_updates_an_older_managed_copy(self, tmp_path: Path) -> None:
        target = tmp_path / "SKILL.md"
        install_skill(_skill(body="# old\n"), target)

        assert install_skill(_skill(body="# new\n"), target) == "updated"
        assert "# new" in target.read_text(encoding="utf-8")

    def test_preserves_user_edits(self, tmp_path: Path) -> None:
        target = tmp_path / "SKILL.md"
        install_skill(_skill(), target)
        target.write_text(
            target.read_text(encoding="utf-8") + "\n# local edit\n",
            encoding="utf-8",
        )

        assert install_skill(_skill(), target) == "user_modified"
        assert "# local edit" in target.read_text(encoding="utf-8")

    def test_force_overwrites_user_edits(self, tmp_path: Path) -> None:
        target = tmp_path / "SKILL.md"
        install_skill(_skill(), target)
        target.write_text("local edit", encoding="utf-8")

        assert install_skill(_skill(), target, force=True) == "overwritten"
        assert "usecli-skill" in target.read_text(encoding="utf-8")

    def test_adopts_an_unmarked_exact_copy(self, tmp_path: Path) -> None:
        target = tmp_path / "SKILL.md"
        skill = _skill()
        target.write_text(skill.content, encoding="utf-8")

        assert install_skill(skill, target) == "adopted"
        assert "usecli-skill" in target.read_text(encoding="utf-8")

    def test_preserves_unmarked_unrelated_content(self, tmp_path: Path) -> None:
        target = tmp_path / "SKILL.md"
        target.write_text("custom", encoding="utf-8")

        assert install_skill(_skill(), target) == "user_modified"
        assert target.read_text(encoding="utf-8") == "custom"

    def test_force_overwrites_unmarked_content(self, tmp_path: Path) -> None:
        target = tmp_path / "SKILL.md"
        target.write_text("custom", encoding="utf-8")

        assert install_skill(_skill(), target, force=True) == "overwritten"
        assert "usecli-skill" in target.read_text(encoding="utf-8")

    def test_marker_for_another_skill_is_user_content(self, tmp_path: Path) -> None:
        target = tmp_path / "SKILL.md"
        install_skill(_skill("other"), target)

        assert install_skill(_skill("demo"), target) == "user_modified"

    def test_force_overwrites_marker_mismatch(self, tmp_path: Path) -> None:
        target = tmp_path / "SKILL.md"
        install_skill(_skill("other"), target)

        assert install_skill(_skill("demo"), target, force=True) == "overwritten"


class TestInstallSkills:
    def test_project_install(self, tmp_path: Path) -> None:
        results = install_skills([_skill()], agents=["claude"], project_root=tmp_path)

        assert len(results) == 1
        assert results[0].path == (
            tmp_path / ".claude" / "skills" / "demo" / "SKILL.md"
        )
        assert results[0].status == "installed"

    def test_default_cwd_and_default_agents(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)

        results = install_skills([_skill()])

        assert len(results) == len(DEFAULT_AGENTS)
        assert (tmp_path / ".claude" / "skills" / "demo" / "SKILL.md").exists()

    def test_duplicate_destinations_are_written_once(self, tmp_path: Path) -> None:
        results = install_skills(
            [_skill()], agents=["codex", "agents"], project_root=tmp_path
        )

        assert len(results) == 1
        assert results[0].path == (
            tmp_path / ".agents" / "skills" / "demo" / "SKILL.md"
        )

    def test_global_install(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        results = install_skills(
            [_skill()],
            agents=["claude"],
            scope="global",
            project_root=tmp_path,
        )

        assert results[0].path == (
            tmp_path / "home" / ".claude" / "skills" / "demo" / "SKILL.md"
        )

    def test_errors_are_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*_args, **_kwargs):
            raise OSError("denied")

        monkeypatch.setattr("usecli.skills.install_skill", boom)

        results = install_skills([_skill()], agents=["claude"], project_root=tmp_path)

        assert results[0].status == "error: denied"

    def test_unknown_scope(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unknown skill scope"):
            install_skills(
                [_skill()],
                agents=["claude"],
                scope="elsewhere",
                project_root=tmp_path,
            )
