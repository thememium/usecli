"""Tests for the public scaffolding API."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import usecli
from usecli import scaffold
from usecli.scaffold import (
    ScaffoldError,
    make_command,
    make_skill,
    make_theme,
    prompt_make_command,
    prompt_make_skill,
    prompt_make_theme,
)
from usecli.shared.config.manager import reset_config


@pytest.fixture(autouse=True)
def reset_usecli_config():
    reset_config()
    yield
    reset_config()


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "mycli"\ndependencies = ["usecli"]\n'
    )
    (tmp_path / "usecli.config.toml").write_text(
        '[usecli]\ncommand_name = "mycli"\n\n'
        "[usecli.paths]\n"
        'commands = "cli/commands"\n'
        'templates = "cli/templates"\n'
        'themes = "cli/themes"\n'
        'skills = "skills"\n'
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestMakeCommand:
    def test_writes_command_with_builtin_template(self, project: Path):
        target = make_command("deploy")

        assert target == project / "cli" / "commands" / "deploy_command.py"
        content = target.read_text()
        assert "class DeployCommand" in content
        assert 'return "deploy"' in content

    def test_uses_project_template(self, project: Path):
        templates = project / "cli" / "templates"
        templates.mkdir(parents=True)
        (templates / "command.py.j2").write_text("{{ class_name }}|{{ command_name }}")

        target = make_command("status")

        assert target.read_text() == "StatusCommand|status"

    def test_grouped_name_keeps_signature(self, project: Path):
        target = make_command("db:migrate")

        assert target.name == "db_migrate_command.py"
        assert 'return "db:migrate"' in target.read_text()

    def test_rejects_existing_command(self, project: Path):
        target = make_command("deploy")
        target.write_text("existing")

        with pytest.raises(ScaffoldError, match="already exists"):
            make_command("deploy")
        assert target.read_text() == "existing"

    def test_force_overwrites_existing_command(self, project: Path):
        target = make_command("deploy")
        target.write_text("existing")

        assert make_command("deploy", force=True) == target
        assert "class DeployCommand" in target.read_text()

    def test_rejects_empty_name(self, project: Path):
        with pytest.raises(ScaffoldError, match="cannot be empty"):
            make_command("   ")

    def test_accepts_explicit_directories(self, project: Path):
        commands_dir = project / "custom" / "commands"

        target = make_command(
            "deploy",
            commands_dir=commands_dir,
            templates_dir=project / "missing-templates",
        )

        assert target == commands_dir / "deploy_command.py"
        assert target.exists()

    def test_project_root_selects_config(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.chdir(project.parent)

        target = make_command("deploy", project_root=project)

        assert target == project / "cli" / "commands" / "deploy_command.py"

    def test_resets_config_when_project_root_differs(
        self, project: Path, monkeypatch: pytest.MonkeyPatch
    ):
        first = MagicMock()
        first.get_project_root.return_value = Path("/other/root")
        second = MagicMock()
        second.get_project_root.return_value = project
        second.get_project_paths.return_value = {
            "commands_dir": project / "commands",
            "templates_dir": project / "templates",
        }

        monkeypatch.setattr(scaffold, "find_project_root", lambda *_: project)
        monkeypatch.setattr(
            scaffold, "get_config", MagicMock(side_effect=[first, second])
        )
        reset = MagicMock()
        monkeypatch.setattr(scaffold, "reset_config", reset)

        target = make_command("deploy")

        reset.assert_called_once()
        assert target == project / "commands" / "deploy_command.py"


class TestMakeTheme:
    def test_writes_theme_with_builtin_template(self, project: Path):
        target = make_theme("dusk")

        assert target == project / "cli" / "themes" / "dusk.toml"
        assert "[colors]" in target.read_text()

    def test_strips_toml_extension(self, project: Path):
        assert make_theme("dusk.toml").name == "dusk.toml"

    def test_increments_duplicate_names(self, project: Path):
        themes = project / "cli" / "themes"
        themes.mkdir(parents=True)
        (themes / "dusk.toml").write_text("existing")
        (themes / "dusk_1.toml").write_text("existing")

        target = make_theme("dusk")

        assert target == themes / "dusk_2.toml"
        assert "[colors]" in target.read_text()

    def test_force_overwrites_existing_theme(self, project: Path):
        target = make_theme("dusk")
        target.write_text("existing")

        assert make_theme("dusk", force=True) == target
        assert "[colors]" in target.read_text()

    @pytest.mark.parametrize("name", ["   ", ".toml"])
    def test_rejects_empty_names(self, project: Path, name: str):
        with pytest.raises(ScaffoldError, match="cannot be empty"):
            make_theme(name)

    def test_uses_project_template(self, project: Path):
        templates = project / "cli" / "templates"
        templates.mkdir(parents=True)
        (templates / "theme.toml.j2").write_text("project theme")

        assert make_theme("dusk").read_text() == "project theme"

    def test_accepts_explicit_directories(self, project: Path):
        themes_dir = project / "custom-themes"

        target = make_theme(
            "dusk",
            themes_dir=themes_dir,
            templates_dir=project / "missing-templates",
        )

        assert target == themes_dir / "dusk.toml"
        assert target.exists()


class TestMakeSkill:
    def test_writes_skill_with_generated_description(self, project: Path):
        target = make_skill("deploy-checks")

        assert target == project / "skills" / "deploy-checks" / "SKILL.md"
        content = target.read_text()
        assert "name: deploy-checks" in content
        assert "Use the deploy-checks skill with the mycli CLI." in content

    def test_normalizes_description(self, project: Path):
        target = make_skill("deploy-checks", 'Check "deploys"\\now')

        content = target.read_text()
        assert 'description: "Check \\"deploys\\"\\\\now"' in content

    def test_falls_back_to_usecli_command_name(self, project: Path):
        (project / "usecli.config.toml").write_text(
            '[usecli.paths]\ncommands = "cli/commands"\ntemplates = "cli/templates"\n'
        )
        reset_config()

        content = make_skill("deploy-checks").read_text()

        assert "with the usecli CLI" in content

    def test_rejects_invalid_name(self, project: Path):
        with pytest.raises(ScaffoldError, match="Invalid skill name"):
            make_skill("Not Valid")

    def test_rejects_existing_skill(self, project: Path):
        target = make_skill("deploy-checks")
        target.write_text("existing")

        with pytest.raises(ScaffoldError, match="already exists"):
            make_skill("deploy-checks")
        assert target.read_text() == "existing"

    def test_force_overwrites_existing_skill(self, project: Path):
        target = make_skill("deploy-checks")
        target.write_text("existing")

        assert make_skill("deploy-checks", force=True) == target
        assert "name: deploy-checks" in target.read_text()

    def test_uses_project_template(self, project: Path):
        templates = project / "cli" / "templates"
        templates.mkdir(parents=True)
        (templates / "project_skill.md.j2").write_text(
            "{{ name }}|{{ description }}|{{ command_name }}"
        )

        target = make_skill("deploy-checks", "Check deploys")

        assert target.read_text() == "deploy-checks|Check deploys|mycli"

    def test_accepts_explicit_directories(self, project: Path):
        skills_dir = project / "custom-skills"
        templates = project / "custom-templates"
        templates.mkdir()
        (templates / "project_skill.md.j2").write_text("{{ name }}")

        target = make_skill(
            "deploy-checks",
            skills_dir=skills_dir,
            templates_dir=templates,
        )

        assert target == skills_dir / "deploy-checks" / "SKILL.md"
        assert target.read_text() == "deploy-checks"


class TestPromptHelpers:
    def test_ask_uses_usecli_prompt(self, monkeypatch: pytest.MonkeyPatch):
        import usecli.ui

        calls: list[tuple[str, str | None]] = []

        def fake_ask(prompt: str, *, default: str | None = None) -> str:
            calls.append((prompt, default))
            return "value"

        monkeypatch.setattr(usecli.ui.Prompt, "ask", staticmethod(fake_ask))

        assert scaffold._ask("Name", default="fallback") == "value"
        assert calls == [("Name", "fallback")]

    def test_ask_returns_empty_string_for_none(self, monkeypatch: pytest.MonkeyPatch):
        import usecli.ui

        monkeypatch.setattr(
            usecli.ui.Prompt, "ask", staticmethod(lambda *_a, **_k: None)
        )

        assert scaffold._ask("Name") == ""

    def test_prompt_make_command(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        calls: list[str] = []

        def fake_ask(prompt: str, *, default: str | None = None) -> str:
            calls.append(prompt)
            return "deploy"

        monkeypatch.setattr(scaffold, "_ask", fake_ask)

        target = prompt_make_command()

        assert calls == ["Command name"]
        assert target.name == "deploy_command.py"

    def test_prompt_make_command_skips_prompt(self, project: Path):
        assert prompt_make_command("deploy").name == "deploy_command.py"

    def test_prompt_make_theme(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        calls: list[str] = []

        def fake_ask(prompt: str, *, default: str | None = None) -> str:
            calls.append(prompt)
            return "dusk"

        monkeypatch.setattr(scaffold, "_ask", fake_ask)

        target = prompt_make_theme()

        assert calls == ["Theme name"]
        assert target.name == "dusk.toml"

    def test_prompt_make_theme_skips_prompt(self, project: Path):
        assert prompt_make_theme("dusk").name == "dusk.toml"

    def test_prompt_make_skill(self, project: Path, monkeypatch: pytest.MonkeyPatch):
        calls: list[tuple[str, str | None]] = []

        def fake_ask(prompt: str, *, default: str | None = None) -> str:
            calls.append((prompt, default))
            return "deploy-checks" if default is None else "Check deploys"

        monkeypatch.setattr(scaffold, "_ask", fake_ask)

        target = prompt_make_skill()

        assert calls == [
            ("Skill name (lowercase-with-hyphens)", None),
            ("Description (optional)", ""),
        ]
        assert 'description: "Check deploys"' in target.read_text()

    def test_prompt_make_skill_skips_prompts(self, project: Path):
        target = prompt_make_skill("deploy-checks", "Check deploys")

        assert 'description: "Check deploys"' in target.read_text()


class TestPublicExports:
    def test_top_level_names_resolve_to_scaffold_api(self):
        assert usecli.ScaffoldError is scaffold.ScaffoldError
        assert usecli.make_command is scaffold.make_command
        assert usecli.make_theme is scaffold.make_theme
        assert usecli.make_skill is scaffold.make_skill
        assert usecli.prompt_make_command is scaffold.prompt_make_command
        assert usecli.prompt_make_theme is scaffold.prompt_make_theme
        assert usecli.prompt_make_skill is scaffold.prompt_make_skill
