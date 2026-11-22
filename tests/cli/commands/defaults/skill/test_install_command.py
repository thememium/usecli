"""Tests for usecli.cli.commands.defaults.skill.install_command."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer

from usecli.cli.commands.defaults.skill import install_command as module
from usecli.cli.commands.defaults.skill.install_command import (
    FRAMEWORK_SKILL_NAME,
    InstallSkillCommand,
    _describe_command,
    _describe_param,
    _discover_project_skills,
    _framework_skill,
    _framework_version,
    _list_data,
    _param_label,
    _print_list,
    _print_results,
    _project_root,
    _prompt_agents,
    _prompt_scope,
    _prompt_skill,
    _select_skills,
    _status_color,
    collect_skill_commands,
    install_framework_skill,
    prompt_skill_install,
    render_skill,
)
from usecli.cli.core.exceptions import UsecliBadParameter
from usecli.cli.core.runtime import NonInteractiveError
from usecli.skills import AGENT_TARGETS, DEFAULT_AGENTS, Skill, SkillError


def _skill(name: str = "demo", *, body: str = "# Demo\n") -> Skill:
    return Skill(
        name=name,
        description=f"{name} description",
        content=f"---\nname: {name}\ndescription: {name} description\n---\n\n{body}",
    )


@pytest.fixture
def app() -> typer.Typer:
    app = typer.Typer()

    @app.command("hello")
    def hello(
        name: str = typer.Argument(..., help="Who to greet"),
        loud: bool = typer.Option(False, "--loud", "-l", help="Uppercase"),
    ) -> None:
        """Say hello."""

    @app.command("nodesc")
    def nodesc() -> None:
        pass

    spec = typer.Typer()

    @spec.command("show")
    def show(
        verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
    ) -> None:
        """Show a spec."""

    app.add_typer(spec, name="spec")
    return app


@pytest.fixture
def command(app: typer.Typer) -> InstallSkillCommand:
    return InstallSkillCommand(app)


@pytest.fixture
def project_skill() -> Skill:
    return _skill("project-skill", body="# Project\n")


@pytest.fixture
def framework_skill() -> Skill:
    return _skill(FRAMEWORK_SKILL_NAME, body="# usecli\n")


@pytest.fixture(autouse=True)
def isolate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    project_skill: Skill,
    framework_skill: Skill,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "_project_root", lambda: tmp_path)
    monkeypatch.setattr(module, "_discover_project_skills", lambda: [project_skill])
    monkeypatch.setattr(module, "_framework_skill", lambda app: framework_skill)
    monkeypatch.setattr(
        "usecli.cli.core.runtime.is_json_mode",
        lambda: False,
    )


class TestCommandMetadata:
    def test_signature(self, command: InstallSkillCommand) -> None:
        assert command.signature() == "skill:install"

    def test_description(self, command: InstallSkillCommand) -> None:
        assert command.description() == "Install bundled skills for coding agents"

    def test_description_for_the_framework_binary(
        self, command: InstallSkillCommand, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module, "_is_framework_binary", lambda: True)

        assert command.description() == "Install the usecli skill for coding agents"

    def test_visible_only_when_project_has_skills(
        self, command: InstallSkillCommand, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module, "_discover_project_skills", list)
        assert command.visible() is False

        monkeypatch.setattr(module, "_discover_project_skills", lambda: [_skill()])
        assert command.visible() is True

    def test_visible_for_the_framework_binary(
        self, command: InstallSkillCommand, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module, "_is_framework_binary", lambda: True)

        assert command.visible() is True

    def test_visible_when_a_project_skill_is_malformed(
        self, command: InstallSkillCommand, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def malformed() -> list[Skill]:
            raise SkillError("bad skill")

        monkeypatch.setattr(module, "_discover_project_skills", malformed)

        assert command.visible() is True


class TestDescriptionRendering:
    def test_collects_all_commands(
        self,
        app: typer.Typer,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "usecli.cli.core.ui.list._skill_install_mode", lambda: "command"
        )
        commands = {entry["name"]: entry for entry in collect_skill_commands(app)}

        assert "skill:install" in commands
        assert "hello" in commands
        assert "nodesc" in commands
        assert "spec" in commands
        assert "spec show" in commands

        assert commands["hello"]["params"] == [
            {"label": "<NAME>", "help": "Who to greet"},
            {"label": "--loud, -l", "help": "Uppercase"},
        ]
        assert commands["spec show"]["params"] == [
            {"label": "--verbose", "help": "Verbose output"}
        ]
        assert commands["hello"]["help"] == "Say hello."

    def test_global_options_are_not_repeated(
        self, app: typer.Typer, command: InstallSkillCommand
    ) -> None:
        commands = {entry["name"]: entry for entry in collect_skill_commands(app)}
        labels = [param["label"] for param in commands["hello"]["params"]]
        assert "--json" not in labels
        assert "--help, -h" not in labels
        assert "--interactive, -i" not in labels

    def test_describe_command_without_click_command(self) -> None:
        described = _describe_command("missing", None, ["miss"])
        assert described == {
            "name": "missing",
            "help": "",
            "aliases": ["miss"],
            "params": [],
        }

    def test_parameter_label_fallbacks(self) -> None:
        class Option:
            param_type_name = "option"
            opts = ()
            secondary_opts = ()
            help = ""

        class Argument:
            param_type_name = "argument"
            name = None
            opts = ()
            secondary_opts = ()
            help = ""

        assert _describe_param(Option()) is None
        assert _param_label(Argument()) == "<ARG>"

    def test_render_skill(self, app: typer.Typer) -> None:
        content = render_skill(app, command_name="mycli")

        assert "name: usecli" in content
        assert "**`mycli`**" in content
        assert "### `hello`" in content
        assert "mycli hello --help" in content
        assert "--loud, -l" in content
        assert "### `spec show`" in content
        assert "mycli spec show --help" in content
        assert "mycli skill:install" in content
        assert "usecli skill:install" in content

    def test_framework_version_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def missing(_name: str) -> str:
            raise PackageNotFoundError("usecli")

        monkeypatch.setattr(module, "version", missing)
        assert _framework_version() == "0.0.0"

    def test_framework_version(self) -> None:
        assert isinstance(_framework_version(), str)

    def test_framework_skill(
        self, app: typer.Typer, command: InstallSkillCommand
    ) -> None:
        skill = _framework_skill(app)

        assert skill.name == FRAMEWORK_SKILL_NAME
        assert "name: usecli" in skill.content
        assert "usecli skill:install" in skill.content


class TestDiscovery:
    def test_project_root_uses_the_finder(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(module, "find_project_root", lambda *_: tmp_path)

        assert _project_root() == tmp_path

    def test_project_root_falls_back_to_cwd(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(module, "find_project_root", lambda *_: None)

        assert _project_root() == tmp_path.resolve()

    def test_project_skills_are_discovered_and_config_is_reused(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, project_skill: Skill
    ) -> None:
        config = MagicMock()
        config.get_project_root.return_value = tmp_path
        config.get_project_skills_dir.return_value = tmp_path / "skills"
        reset = MagicMock()
        monkeypatch.setattr(module, "get_config", lambda: config)
        monkeypatch.setattr(module, "reset_config", reset)
        monkeypatch.setattr(
            module, "discover_skills", lambda directory: [project_skill]
        )

        assert _discover_project_skills() == [project_skill]
        reset.assert_not_called()

    def test_config_is_reset_when_the_root_changes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, project_skill: Skill
    ) -> None:
        first = MagicMock()
        first.get_project_root.return_value = tmp_path / "other"
        second = MagicMock()
        second.get_project_skills_dir.return_value = tmp_path / "skills"
        configs = iter([first, second])
        reset = MagicMock()
        monkeypatch.setattr(module, "get_config", lambda: next(configs))
        monkeypatch.setattr(module, "reset_config", reset)
        monkeypatch.setattr(
            module, "discover_skills", lambda directory: [project_skill]
        )

        assert _discover_project_skills() == [project_skill]
        reset.assert_called_once()

    def test_project_selector_uses_project_skills_only(
        self, app: typer.Typer, project_skill: Skill
    ) -> None:
        assert _select_skills(app, None) == [project_skill]

    def test_framework_selector_uses_the_usecli_skill_only(
        self,
        app: typer.Typer,
        monkeypatch: pytest.MonkeyPatch,
        framework_skill: Skill,
    ) -> None:
        monkeypatch.setattr(module, "_is_framework_binary", lambda: True)

        assert _select_skills(app, None) == [framework_skill]

    def test_select_skills_filters(
        self, app: typer.Typer, project_skill: Skill
    ) -> None:
        assert _select_skills(app, ["project-skill"]) == [project_skill]


class TestStatusAndOutput:
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            ("error: denied", module.COLOR.ERROR),
            ("user_modified", module.COLOR.WARNING),
            ("installed", module.COLOR.SUCCESS),
            ("unknown", module.COLOR.FOREGROUND),
        ],
    )
    def test_status_colors(self, status: str, expected: str) -> None:
        assert _status_color(status) == expected

    def test_list_data(self, tmp_path: Path, project_skill: Skill) -> None:
        data = _list_data(
            [project_skill],
            ["claude"],
            scope="project",
            project_root=tmp_path,
        )

        assert data["skills"][0]["name"] == "project-skill"
        assert data["agents"][0]["name"] == "claude"
        assert data["agents"][0]["path"] == str(tmp_path / ".claude" / "skills")

    def test_print_list(
        self, capsys: pytest.CaptureFixture[str], tmp_path: Path, project_skill: Skill
    ) -> None:
        _print_list(
            _list_data(
                [project_skill],
                ["claude"],
                scope="project",
                project_root=tmp_path,
            )
        )
        out = capsys.readouterr().out
        assert "Bundled skills" in out
        assert "project-skill" in out

    def _results(self, *statuses: str) -> dict[str, object]:
        return {
            "installed": [
                {
                    "skill": "demo",
                    "agent": "claude",
                    "path": f"/tmp/{status}",
                    "status": status,
                }
                for status in statuses
            ],
            "errors": [],
        }

    def test_print_results_normal(self, capsys: pytest.CaptureFixture[str]) -> None:
        _print_results(self._results("installed", "updated"))

        out = capsys.readouterr().out
        assert "installed" in out
        assert "updated" in out

    def test_print_results_warns_about_user_edits(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _print_results(self._results("user_modified"))

        out = " ".join(capsys.readouterr().out.split())
        assert "Re-run with --force" in out

    def test_print_results_reports_errors(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        data = self._results("error: denied")
        data["errors"] = ["demo -> claude: error: denied"]
        _print_results(data)

        assert "error: denied" in capsys.readouterr().out


class TestInteractivePrompts:
    def test_scope_is_kept_when_global(self) -> None:
        assert _prompt_scope(True) is True

    def test_scope_asks_with_a_menu(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[tuple[list[str], str]] = []

        def select(options: list[str], *, title: str) -> str:
            calls.append((options, title))
            return "Project"

        monkeypatch.setattr(module.Menu, "select", select)

        assert _prompt_scope(False) is False
        assert calls == [(["Project", "Global"], "Installation scope")]

    def test_scope_can_select_global(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(module.Menu, "select", lambda options, title: "Global")

        assert _prompt_scope(False) is True

    def test_scope_cancel_defaults_to_project(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(module.Menu, "select", lambda options, title: None)

        assert _prompt_scope(False) is False

    def test_agents_are_kept_when_supplied(self) -> None:
        assert _prompt_agents(["codex"]) == ["codex"]

    def test_agents_are_selected_from_the_menu(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            module.Menu,
            "multi_select",
            lambda options, title: ["codex", "cursor"],
        )

        assert _prompt_agents(None) == ["codex", "cursor"]

    def test_agent_selection_falls_back_to_defaults(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(module.Menu, "multi_select", lambda options, title: [])

        assert _prompt_agents(None) == list(DEFAULT_AGENTS)
        assert "using claude, codex, cursor" in capsys.readouterr().out

    def test_agent_choices_limit_the_menu(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[list[str]] = []

        def multi_select(options: list[str], *, title: str) -> list[str]:
            seen.append(options)
            return ["codex"]

        monkeypatch.setattr(module.Menu, "multi_select", multi_select)

        assert _prompt_agents(None, choices=["codex", "cursor"]) == ["codex"]
        assert seen == [["codex", "cursor"]]

    def test_single_agent_choice_skips_the_menu(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            module.Menu,
            "multi_select",
            lambda *args, **kwargs: pytest.fail("menu should not be shown"),
        )

        assert _prompt_agents(None, choices=["codex"]) == ["codex"]

    def test_agent_choice_fallback_stays_within_choices(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(module.Menu, "multi_select", lambda options, title: [])

        assert _prompt_agents(None, choices=["pi", "omp"]) == ["pi", "omp"]
        assert "using pi, omp" in capsys.readouterr().out

    def test_unknown_agent_choices_fall_back_to_all_targets(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[list[str]] = []

        def multi_select(options: list[str], *, title: str) -> list[str]:
            seen.append(options)
            return ["claude"]

        monkeypatch.setattr(module.Menu, "multi_select", multi_select)

        assert _prompt_agents(None, choices=["not-an-agent"]) == ["claude"]
        assert seen == [list(AGENT_TARGETS)]

    def test_skill_prompt_is_skipped_for_one_skill(
        self, monkeypatch: pytest.MonkeyPatch, project_skill: Skill
    ) -> None:
        monkeypatch.setattr(
            module.Menu,
            "multi_select",
            lambda *args, **kwargs: pytest.fail("menu should not be shown"),
        )

        assert _prompt_skill([project_skill]) == [project_skill]

    def test_skills_are_selected_from_the_menu(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        first = _skill("first")
        second = _skill("second")

        def select(labels: list[str], *, title: str) -> list[str]:
            assert title == "Select skills to install"
            return [labels[1]]

        monkeypatch.setattr(module.Menu, "multi_select", select)

        assert _prompt_skill([first, second]) == [second]

    def test_skill_selection_falls_back_to_all(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        first = _skill("first")
        second = _skill("second")
        monkeypatch.setattr(module.Menu, "multi_select", lambda options, title: [])

        assert _prompt_skill([first, second]) == [first, second]
        assert "using all 2 bundled skills" in capsys.readouterr().out

    def test_single_skill_selection(
        self, monkeypatch: pytest.MonkeyPatch, project_skill: Skill
    ) -> None:
        second = _skill("second")

        def select(labels: list[str], *, title: str) -> str:
            assert title == "Select a skill to install"
            return labels[1]

        monkeypatch.setattr(module.Menu, "select", select)

        assert _prompt_skill([project_skill, second], single=True) == [second]

    def test_single_skill_selection_can_be_cancelled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        first = _skill("first")
        second = _skill("second")
        monkeypatch.setattr(module.Menu, "select", lambda options, title: None)

        assert _prompt_skill([first, second], single=True) == [first, second]


class TestHandle:
    def test_project_install(
        self, command: InstallSkillCommand, tmp_path: Path
    ) -> None:
        data = command.handle(agent=["claude"])

        assert data["scope"] == "project"
        assert data["skills"] == ["project-skill"]
        assert len(data["installed"]) == 1
        assert (tmp_path / ".claude" / "skills" / "project-skill" / "SKILL.md").exists()
        assert not (tmp_path / ".claude" / "skills" / "usecli").exists()

    def test_framework_install_uses_only_the_usecli_skill(
        self,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(module, "_is_framework_binary", lambda: True)

        data = command.handle(agent=["claude"])

        assert data["scope"] == "project"
        assert data["skills"] == ["usecli"]
        assert (tmp_path / ".claude" / "skills" / "usecli" / "SKILL.md").exists()
        assert not (tmp_path / ".claude" / "skills" / "project-skill").exists()

    def test_skill_filter(self, command: InstallSkillCommand, tmp_path: Path) -> None:
        data = command.handle(agent=["claude"], skill=["project-skill"])

        assert data["skills"] == ["project-skill"]
        assert not (tmp_path / ".claude" / "skills" / "usecli").exists()

    def test_global_install(
        self,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        data = command.handle(global_=True, agent=["claude"], skill=["project-skill"])

        assert data["scope"] == "global"
        assert (
            tmp_path / "home" / ".claude" / "skills" / "project-skill" / "SKILL.md"
        ).exists()

    def test_path_requires_exactly_one_skill(
        self,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            module,
            "_discover_project_skills",
            lambda: [_skill("project-skill"), _skill("second-skill")],
        )

        with pytest.raises(UsecliBadParameter, match="exactly one skill"):
            command.handle(path=tmp_path / "custom", agent=[])

    def test_path_infers_skill_from_directory_name(
        self, command: InstallSkillCommand, tmp_path: Path
    ) -> None:
        target = tmp_path / "project-skill"

        data = command.handle(path=target)

        assert data["scope"] == "custom"
        assert data["skills"] == ["project-skill"]
        assert (target / "SKILL.md").exists()

    def test_path_with_selected_skill(
        self, command: InstallSkillCommand, tmp_path: Path
    ) -> None:
        target = tmp_path / "custom"

        data = command.handle(path=target, skill=["project-skill"])

        assert data["skills"] == ["project-skill"]
        assert data["installed"][0]["agent"] == "custom"
        assert (target / "SKILL.md").exists()

    def test_path_and_global_conflict(
        self, command: InstallSkillCommand, tmp_path: Path
    ) -> None:
        with pytest.raises(UsecliBadParameter, match="--global and --path"):
            command.handle(global_=True, path=tmp_path / "custom")

    def test_path_and_agent_conflict(
        self, command: InstallSkillCommand, tmp_path: Path
    ) -> None:
        with pytest.raises(UsecliBadParameter, match="--path and --agent"):
            command.handle(path=tmp_path / "custom", agent=["claude"])

    def test_unknown_skill(self, command: InstallSkillCommand) -> None:
        with pytest.raises(UsecliBadParameter, match="Unknown skill"):
            command.handle(agent=["claude"], skill=["missing"])

    def test_unknown_agent(self, command: InstallSkillCommand) -> None:
        with pytest.raises(UsecliBadParameter, match="Unknown agent"):
            command.handle(agent=["missing"])

    def test_list(
        self, command: InstallSkillCommand, capsys: pytest.CaptureFixture[str]
    ) -> None:
        data = command.handle(list_=True, agent=["claude"])

        assert data["skills"][0]["name"] == "project-skill"
        assert data["agents"][0]["name"] == "claude"
        assert "Bundled skills" in capsys.readouterr().out

    def test_list_global(
        self,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        data = command.handle(list_=True, global_=True, agent=["claude"])

        assert data["scope"] == "global"
        assert data["agents"][0]["path"] == str(
            tmp_path / "home" / ".claude" / "skills"
        )

    def test_second_install_is_unchanged(self, command: InstallSkillCommand) -> None:
        command.handle(agent=["claude"], skill=["project-skill"])
        data = command.handle(agent=["claude"], skill=["project-skill"])

        assert data["installed"][0]["status"] == "already_installed"

    def test_user_edits_are_preserved_and_warned(
        self,
        command: InstallSkillCommand,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        command.handle(agent=["claude"], skill=["project-skill"])
        target = tmp_path / ".claude" / "skills" / "project-skill" / "SKILL.md"
        target.write_text("local edit", encoding="utf-8")

        data = command.handle(agent=["claude"], skill=["project-skill"])

        assert data["installed"][0]["status"] == "user_modified"
        out = " ".join(capsys.readouterr().out.split())
        assert "Re-run with --force" in out

    def test_force_overwrites_user_edits(
        self, command: InstallSkillCommand, tmp_path: Path
    ) -> None:
        command.handle(agent=["claude"], skill=["project-skill"])
        target = tmp_path / ".claude" / "skills" / "project-skill" / "SKILL.md"
        target.write_text("local edit", encoding="utf-8")

        data = command.handle(
            agent=["claude"],
            skill=["project-skill"],
            force=True,
        )

        assert data["installed"][0]["status"] == "overwritten"

    def test_install_error_is_reported(
        self,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def boom(*_args, **_kwargs):
            raise OSError("denied")

        monkeypatch.setattr(module, "install_skill", boom)

        data = command.handle(
            path=tmp_path / "custom",
            skill=["project-skill"],
        )

        assert data["errors"]
        assert "error: denied" in capsys.readouterr().out

    def test_json_mode_skips_human_output(
        self,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(
            "usecli.cli.core.runtime.is_json_mode",
            lambda: True,
        )

        data = command.handle(agent=["claude"], skill=["project-skill"])

        assert data["installed"][0]["status"] == "installed"
        assert capsys.readouterr().out == ""

    def test_interactive_options_are_applied(
        self,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
        project_skill: Skill,
        tmp_path: Path,
    ) -> None:
        calls: list[tuple[str, object]] = []

        def prompt_scope(global_: bool) -> bool:
            calls.append(("scope", global_))
            return True

        def prompt_agents(agent: list[str] | None) -> list[str] | None:
            calls.append(("agents", agent))
            return ["claude"]

        def prompt_skill(skills: list[Skill], *, single: bool = False) -> list[Skill]:
            calls.append(("skills", single))
            return [project_skill]

        monkeypatch.setattr(module, "_prompt_scope", prompt_scope)
        monkeypatch.setattr(module, "_prompt_agents", prompt_agents)
        monkeypatch.setattr(module, "_prompt_skill", prompt_skill)
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        data = command.handle(interactive=True)

        assert data["scope"] == "global"
        assert data["skills"] == ["project-skill"]
        assert calls == [
            ("scope", False),
            ("agents", None),
            ("skills", False),
        ]
        assert (
            tmp_path / "home" / ".claude" / "skills" / "project-skill" / "SKILL.md"
        ).exists()

    def test_interactive_path_skips_scope_and_agents(
        self,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
        project_skill: Skill,
        tmp_path: Path,
    ) -> None:
        def fail(*_args, **_kwargs):
            pytest.fail("scope and agent prompts should be skipped for --path")

        monkeypatch.setattr(module, "_prompt_scope", fail)
        monkeypatch.setattr(module, "_prompt_agents", fail)
        monkeypatch.setattr(
            module,
            "_prompt_skill",
            lambda skills, *, single=False: [project_skill],
        )

        target = tmp_path / "custom"
        data = command.handle(interactive=True, path=target)

        assert data["scope"] == "custom"
        assert (target / "SKILL.md").exists()

    def test_interactive_install_overwrites_local_edits(
        self,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        command.handle(agent=["claude"], skill=["project-skill"])
        target = tmp_path / ".claude" / "skills" / "project-skill" / "SKILL.md"
        target.write_text("local edit", encoding="utf-8")
        monkeypatch.setattr(module, "_prompt_scope", lambda global_: False)

        data = command.handle(
            interactive=True,
            agent=["claude"],
            skill=["project-skill"],
        )

        assert data["installed"][0]["status"] == "overwritten"
        assert "local edit" not in target.read_text(encoding="utf-8")

    def test_interactive_list_skips_prompts(
        self,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def fail(*_args, **_kwargs):
            pytest.fail("list mode should not prompt")

        monkeypatch.setattr(module, "_prompt_scope", fail)
        monkeypatch.setattr(module, "_prompt_agents", fail)
        monkeypatch.setattr(module, "_prompt_skill", fail)

        data = command.handle(interactive=True, list_=True, agent=["claude"])

        assert data["skills"][0]["name"] == "project-skill"
        assert "Bundled skills" in capsys.readouterr().out

    def test_interactive_mode_is_unavailable_in_json_mode(
        self,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "usecli.cli.core.runtime.is_json_mode",
            lambda: True,
        )

        with pytest.raises(NonInteractiveError, match="unavailable in JSON mode"):
            command.handle(interactive=True)


def test_install_framework_skill_uses_project_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = typer.Typer()
    skill = _skill("usecli")
    seen: dict[str, object] = {}

    monkeypatch.setattr(module, "_framework_skill", lambda _app: skill)

    def fake_install(skills, **kwargs):
        seen["skills"] = list(skills)
        seen["kwargs"] = kwargs
        return []

    monkeypatch.setattr(module, "install_skills", fake_install)
    project_root = Path("/tmp/usecli-project")

    result = install_framework_skill(
        app,
        project_root=project_root,
        agents=["claude"],
        scope="global",
        force=True,
    )

    assert result == []
    assert seen == {
        "skills": [skill],
        "kwargs": {
            "agents": ["claude"],
            "scope": "global",
            "project_root": project_root,
            "force": True,
        },
    }


class TestInteractiveInstall:
    def test_prompts_scope_agents_and_installs(
        self,
        app: typer.Typer,
        command: InstallSkillCommand,
        project_skill: Skill,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        calls: list[tuple[str, object]] = []

        def prompt_scope(global_: bool) -> bool:
            calls.append(("scope", global_))
            return False

        def prompt_agents(agent: list[str] | None) -> list[str] | None:
            calls.append(("agents", agent))
            return ["claude"]

        monkeypatch.setattr(module, "_prompt_scope", prompt_scope)
        monkeypatch.setattr(module, "_prompt_agents", prompt_agents)

        command.handle(agent=["claude"], skill=[project_skill.name])
        target = tmp_path / ".claude" / "skills" / project_skill.name / "SKILL.md"
        target.write_text("local edit", encoding="utf-8")

        data = prompt_skill_install(app)

        assert calls == [("scope", False), ("agents", None)]
        assert data["scope"] == "project"
        assert data["skills"] == [project_skill.name]
        assert data["installed"][0]["status"] == "overwritten"
        assert "local edit" not in target.read_text(encoding="utf-8")

    def test_prompts_for_a_skill_when_several_exist(
        self,
        app: typer.Typer,
        project_skill: Skill,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        second = _skill("second")
        prompted: list[list[Skill]] = []

        def prompt_skill(skills: list[Skill], *, single: bool = False) -> list[Skill]:
            prompted.append(skills)
            return [second]

        monkeypatch.setattr(
            module, "_select_skills", lambda app, names: [project_skill, second]
        )
        monkeypatch.setattr(module, "_prompt_skill", prompt_skill)
        monkeypatch.setattr(module, "_prompt_scope", lambda global_: False)
        monkeypatch.setattr(module, "_prompt_agents", lambda agent: ["claude"])

        data = prompt_skill_install(app)

        assert prompted == [[project_skill, second]]
        assert data["skills"] == ["second"]

    def test_is_unavailable_in_json_mode(
        self,
        app: typer.Typer,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "usecli.cli.core.runtime.is_json_mode",
            lambda: True,
        )

        with pytest.raises(NonInteractiveError, match="unavailable in JSON mode"):
            prompt_skill_install(app)

    def test_malformed_project_skills_raise_bad_parameter(
        self,
        app: typer.Typer,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        def fail() -> list[Skill]:
            raise SkillError("bad skill")

        monkeypatch.setattr(module, "_discover_project_skills", fail)
        monkeypatch.setattr(module, "_prompt_scope", lambda global_: False)
        monkeypatch.setattr(module, "_prompt_agents", lambda agent: ["claude"])

        with pytest.raises(UsecliBadParameter, match="bad skill"):
            prompt_skill_install(app)

    def test_uses_a_skill_folder(
        self,
        app: typer.Typer,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        skills_dir = tmp_path / "custom-skills"
        skill_dir = skills_dir / "custom"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: custom\ndescription: Custom skill\n---\n\n# Custom\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(module, "_prompt_scope", lambda global_: False)
        monkeypatch.setattr(module, "_prompt_agents", lambda agent: ["claude"])

        data = prompt_skill_install(
            app,
            skills_dir=skills_dir,
            show_skills=False,
            print_results=False,
        )

        assert data["skills"] == ["custom"]
        assert (tmp_path / ".claude" / "skills" / "custom" / "SKILL.md").exists()

    def test_uses_explicit_skills_and_skips_the_scope_prompt(
        self,
        app: typer.Typer,
        project_skill: Skill,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(
            module,
            "_prompt_scope",
            lambda *args, **kwargs: pytest.fail("scope prompt should be skipped"),
        )
        monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")

        data = prompt_skill_install(
            app,
            skills=[project_skill],
            scope="global",
            show_agents=False,
            show_skills=False,
            print_results=False,
            project_root=tmp_path,
        )

        assert data["scope"] == "global"
        assert data["skills"] == [project_skill.name]
        assert (
            tmp_path / "home" / ".claude" / "skills" / project_skill.name / "SKILL.md"
        ).exists()

    def test_agent_choices_are_passed_to_the_prompt(
        self,
        app: typer.Typer,
        project_skill: Skill,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        offered: list[list[str]] = []

        def prompt_agents(
            agent: list[str] | None, *, choices: list[str] | None = None
        ) -> list[str] | None:
            offered.append(list(choices or []))
            return ["codex"]

        monkeypatch.setattr(module, "_prompt_scope", lambda global_: False)
        monkeypatch.setattr(module, "_prompt_agents", prompt_agents)

        data = prompt_skill_install(
            app,
            skills=[project_skill],
            agents=["codex", "cursor"],
            show_skills=False,
            print_results=False,
            project_root=tmp_path,
        )

        assert offered == [["codex", "cursor"]]
        assert data["installed"][0]["agent"] == "codex"

    def test_disabled_prompts_use_their_defaults(
        self,
        app: typer.Typer,
        project_skill: Skill,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        def fail(*args: object, **kwargs: object) -> None:
            pytest.fail("disabled prompts should not run")

        monkeypatch.setattr(module, "_prompt_scope", fail)
        monkeypatch.setattr(module, "_prompt_agents", fail)
        monkeypatch.setattr(module, "_prompt_skill", fail)

        data = prompt_skill_install(
            app,
            skills=[project_skill],
            show_scope=False,
            show_agents=False,
            show_skills=False,
            print_results=False,
            project_root=tmp_path,
        )

        assert data["scope"] == "project"
        assert {entry["agent"] for entry in data["installed"]} == set(DEFAULT_AGENTS)

    def test_print_results_can_be_disabled(
        self,
        app: typer.Typer,
        project_skill: Skill,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(module, "_prompt_scope", lambda global_: False)
        monkeypatch.setattr(module, "_prompt_agents", lambda agent: ["claude"])

        prompt_skill_install(
            app,
            skills=[project_skill],
            show_skills=False,
            print_results=False,
            project_root=tmp_path,
        )

        assert capsys.readouterr().out == ""

    def test_invalid_scope_raises_bad_parameter(self, app: typer.Typer) -> None:
        with pytest.raises(UsecliBadParameter, match="scope must be"):
            prompt_skill_install(app, scope="everywhere")
