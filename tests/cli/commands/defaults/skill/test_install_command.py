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
    _select_skills,
    _status_color,
    collect_skill_commands,
    render_skill,
)
from usecli.cli.core.exceptions import UsecliBadParameter
from usecli.skills import Skill, SkillError


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
        self, app: typer.Typer, command: InstallSkillCommand
    ) -> None:
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
