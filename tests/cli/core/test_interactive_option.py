import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from click.exceptions import Exit
from typer.core import TyperOption

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from usecli import app, run_app
from usecli.cli.core.base_command import CustomHelpCommand, NestedCommandRegistry


@pytest.fixture
def clean_registry():
    registry = NestedCommandRegistry()
    registry._groups = {}
    registry._group_commands = {}
    yield registry
    registry._groups = {}
    registry._group_commands = {}


def test_custom_help_command_adds_interactive_option():
    cmd = CustomHelpCommand(name="test")

    interactive_params = [
        p
        for p in cmd.params
        if isinstance(p, TyperOption) and ("--interactive" in p.opts or "-i" in p.opts)
    ]

    assert len(interactive_params) == 1


def test_custom_help_command_invoke_removes_interactive_before_super():
    cmd = CustomHelpCommand(name="test")
    ctx = MagicMock()
    ctx.params = {"interactive": False, "other_param": "value"}

    with patch("usecli.cli.core.base_command.TyperCommand.invoke") as mock_super:
        cmd.invoke(ctx)

    assert "interactive" not in ctx.params
    assert "other_param" in ctx.params
    mock_super.assert_called_once_with(ctx)


def test_custom_help_command_invoke_calls_run_interactive():
    cmd = CustomHelpCommand(name="test")
    ctx = MagicMock()
    ctx.params = {"interactive": True}
    ctx.command_path = "usecli about"

    with (
        patch("usecli.app", app),
        patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.run_interactive"
        ) as mock_run,
        pytest.raises(Exit),
    ):
        cmd.invoke(ctx)

    mock_run.assert_called_once_with(app, cmd_parts=["about"])
    assert "interactive" not in ctx.params


def test_main_interactive_calls_run_interactive():
    ctx = MagicMock()
    ctx.invoked_subcommand = "about"

    with (
        patch(
            "usecli.cli.commands.defaults.base.internal.fzf_command.run_interactive"
        ) as mock_run,
        pytest.raises(typer.Exit),
    ):
        run_app(ctx=ctx, version=False, help=False, interactive=True)

    mock_run.assert_called_once_with(app, cmd_parts=["about"])


def test_group_callback_registers_interactive_option(clean_registry):
    group_app = clean_registry.get_or_create_group(typer.Typer(), "config")
    click_group = typer.main.get_command(group_app)
    option_flags = [
        opt.opts for opt in click_group.params if isinstance(opt, TyperOption)
    ]

    assert any("--interactive" in opts or "-i" in opts for opts in option_flags)
