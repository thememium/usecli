"""Tests for usecli.cli.commands.defaults.skill.install_command."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from pathlib import Path

import pytest
import typer

from usecli.cli.commands.defaults.skill import install_command as module
from usecli.cli.commands.defaults.skill.install_command import (
    DEFAULT_AGENTS,
    InstallSkillCommand,
    _describe_command,
    _describe_param,
    _framework_version,
    _param_label,
    _parse_agents,
    _target_dir,
    collect_skill_commands,
    render_skill,
    write_skill,
)
from usecli.cli.core.exceptions import UsecliBadParameter


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


@pytest.fixture(autouse=True)
def isolate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "find_project_root", lambda *_: tmp_path)
    monkeypatch.setattr(module, "get_script_command_name", lambda default=None: "mycli")
    monkeypatch.setattr(
        "usecli.cli.core.runtime.is_json_mode",
        lambda: False,
    )


class TestCommandMetadata:
    def test_signature(self, command: InstallSkillCommand) -> None:
        assert command.signature() == "skill:install"

    def test_description(self, command: InstallSkillCommand) -> None:
        assert command.description() == "Install a usecli skill for coding agents"


class TestAgentParsing:
    def test_defaults_when_omitted(self) -> None:
        assert _parse_agents(None) == list(DEFAULT_AGENTS)
        assert _parse_agents([]) == list(DEFAULT_AGENTS)

    def test_all_and_aliases(self) -> None:
        assert _parse_agents(["all"]) == list(DEFAULT_AGENTS)
        assert _parse_agents(["agents,claude"]) == ["codex", "claude-code"]

    def test_deduplicates_and_skips_blanks(self) -> None:
        assert _parse_agents(["claude-code,,claude-code,"]) == ["claude-code"]

    def test_unknown_agent(self) -> None:
        with pytest.raises(UsecliBadParameter, match="Unknown agent"):
            _parse_agents(["unknown"])

    def test_empty_selection(self) -> None:
        with pytest.raises(UsecliBadParameter, match="At least one agent"):
            _parse_agents([" , "])


class TestTargetDir:
    def test_project_path(self, tmp_path: Path) -> None:
        assert (
            _target_dir("claude-code", global_=False, project_root=tmp_path)
            == tmp_path / ".claude" / "skills" / "usecli"
        )

    def test_global_path(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert (
            _target_dir("codex", global_=True, project_root=tmp_path)
            == tmp_path / ".agents" / "skills" / "usecli"
        )


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

    def test_framework_version_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def missing(_name: str) -> str:
            raise PackageNotFoundError("usecli")

        monkeypatch.setattr(module, "version", missing)
        assert _framework_version() == "0.0.0"


class TestWriteSkill:
    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        target = tmp_path / "one" / "two" / "SKILL.md"
        assert write_skill(target, "content", force=False) == "created"
        assert target.read_text(encoding="utf-8") == "content"

    def test_unchanged(self, tmp_path: Path) -> None:
        target = tmp_path / "SKILL.md"
        write_skill(target, "content", force=False)
        assert write_skill(target, "content", force=False) == "unchanged"

    def test_skips_different_content_without_force(self, tmp_path: Path) -> None:
        target = tmp_path / "SKILL.md"
        target.write_text("old", encoding="utf-8")
        assert write_skill(target, "new", force=False) == "skipped"
        assert target.read_text(encoding="utf-8") == "old"

    def test_updates_different_content_with_force(self, tmp_path: Path) -> None:
        target = tmp_path / "SKILL.md"
        target.write_text("old", encoding="utf-8")
        assert write_skill(target, "new", force=True) == "updated"
        assert target.read_text(encoding="utf-8") == "new"


class TestHandle:
    def test_project_defaults(
        self, command: InstallSkillCommand, tmp_path: Path
    ) -> None:
        data = command.handle()

        assert data["scope"] == "project"
        assert data["command_name"] == "mycli"
        assert len(data["installed"]) == 3
        assert (tmp_path / ".claude" / "skills" / "usecli" / "SKILL.md").exists()
        assert (tmp_path / ".agents" / "skills" / "usecli" / "SKILL.md").exists()
        assert (tmp_path / ".cursor" / "skills" / "usecli" / "SKILL.md").exists()

    def test_global_selected_agent(
        self,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        data = command.handle(global_=True, agent=["claude-code"])

        assert data["scope"] == "global"
        assert len(data["installed"]) == 1
        assert data["installed"][0]["agent"] == "claude-code"
        assert (tmp_path / ".claude" / "skills" / "usecli" / "SKILL.md").exists()
        assert not (tmp_path / ".agents").exists()

    def test_path_override(self, command: InstallSkillCommand, tmp_path: Path) -> None:
        target = tmp_path / "custom"

        data = command.handle(path=target)

        assert data["scope"] == "custom"
        assert data["installed"] == [
            {
                "agent": "custom",
                "path": str(target / "SKILL.md"),
                "status": "created",
            }
        ]
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
            command.handle(path=tmp_path / "custom", agent=["claude-code"])

    def test_second_run_is_unchanged(
        self, command: InstallSkillCommand, tmp_path: Path
    ) -> None:
        command.handle(agent=["claude-code"])
        data = command.handle(agent=["claude-code"])

        assert data["installed"][0]["status"] == "unchanged"

    def test_skips_and_warns_on_existing_content(
        self, command: InstallSkillCommand, tmp_path: Path
    ) -> None:
        target = tmp_path / ".claude" / "skills" / "usecli" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("old", encoding="utf-8")

        data = command.handle(agent=["claude-code"])

        assert data["installed"][0]["status"] == "skipped"
        assert target.read_text(encoding="utf-8") == "old"

    def test_force_overwrites(
        self, command: InstallSkillCommand, tmp_path: Path
    ) -> None:
        target = tmp_path / ".claude" / "skills" / "usecli" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_text("old", encoding="utf-8")

        data = command.handle(agent=["claude-code"], force=True)

        assert data["installed"][0]["status"] == "updated"
        assert "name: usecli" in target.read_text(encoding="utf-8")

    def test_json_mode_returns_data(
        self,
        command: InstallSkillCommand,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "usecli.cli.core.runtime.is_json_mode",
            lambda: True,
        )

        data = command.handle(agent=["claude-code"])

        assert data["skill"] == "usecli"
        assert data["installed"][0]["status"] == "created"
