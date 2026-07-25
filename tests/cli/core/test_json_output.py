"""Integration tests for the framework-wide JSON output mode."""

from __future__ import annotations

import json
from collections.abc import Iterator
from importlib import import_module
from unittest.mock import patch

import pytest
from click.exceptions import Exit
from click.testing import CliRunner

import usecli
from usecli import BaseCommand
from usecli.cli.core.base_command import CustomHelpCommand, NestedCommandRegistry
from usecli.cli.core.exceptions import UsecliError


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def registered_json_commands() -> Iterator[None]:
    """Register deterministic leaf and nested commands on the framework app."""

    class JsonLeafCommand(BaseCommand):
        def handle(self) -> None:
            return None

        def signature(self) -> str:
            return "json-contract-leaf"

        def description(self) -> str:
            return "Exercise JSON output on a leaf command"

    class JsonNestedCommand(BaseCommand):
        def handle(self) -> None:
            return None

        def signature(self) -> str:
            return "json-contract-group show"

        def description(self) -> str:
            return "Exercise JSON output on a nested command"

    class JsonDiagnosticCommand(BaseCommand):
        def handle(self) -> None:
            print("plain diagnostic")
            usecli.console.print("[bold red]rich diagnostic[/bold red]")

        def signature(self) -> str:
            return "json-contract-diagnostics"

        def description(self) -> str:
            return "Exercise JSON stream separation"

    class JsonUsecliErrorCommand(BaseCommand):
        def handle(self) -> None:
            raise UsecliError("framework failure")

        def signature(self) -> str:
            return "json-contract-usecli-error"

        def description(self) -> str:
            return "Exercise structured framework errors"

    class JsonUnhandledCommand(BaseCommand):
        def handle(self) -> None:
            raise RuntimeError("unexpected failure")

        def signature(self) -> str:
            return "json-contract-unhandled"

        def description(self) -> str:
            return "Exercise structured unhandled errors"

    class JsonExitCommand(BaseCommand):
        def handle(self) -> None:
            raise Exit(7)

        def signature(self) -> str:
            return "json-contract-exit"

        def description(self) -> str:
            return "Exercise structured explicit exits"

    def structured_result():
        return {"items": [1, 2]}

    def nonserializable_result():
        return {1, 2}

    def literal_value(value: str) -> None:
        print(value)

    existing_names = {command.name for command in usecli.app.registered_commands}
    command_types = (
        ("json-contract-leaf", JsonLeafCommand),
        ("json-contract-diagnostics", JsonDiagnosticCommand),
        ("json-contract-usecli-error", JsonUsecliErrorCommand),
        ("json-contract-unhandled", JsonUnhandledCommand),
        ("json-contract-exit", JsonExitCommand),
    )
    for command_name, command_type in command_types:
        if command_name not in existing_names:
            command_type(usecli.app)

    if "json-contract-structured" not in existing_names:
        usecli.app.command(
            name="json-contract-structured",
            help="Exercise structured command results",
            cls=CustomHelpCommand,
        )(structured_result)
    if "json-contract-nonserializable" not in existing_names:
        usecli.app.command(
            name="json-contract-nonserializable",
            help="Exercise JSON serialization failures",
            cls=CustomHelpCommand,
        )(nonserializable_result)
    if "json-contract-literal" not in existing_names:
        usecli.app.command(
            name="json-contract-literal",
            help="Exercise option delimiter handling",
            cls=CustomHelpCommand,
        )(literal_value)

    registry = NestedCommandRegistry()
    if "json-contract-group" not in registry._groups:
        JsonNestedCommand(usecli.app)

    yield


def _invoke_json(runner: CliRunner, arguments: list[str]):
    typer_main = import_module("typer.main")
    return runner.invoke(typer_main.get_command(usecli.app), arguments)


def _assert_success(result, expected_data: object) -> None:
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"ok": True, "data": expected_data}


def _assert_error(
    result,
    *,
    code: int,
    error_type: str,
    message: str,
) -> None:
    assert result.exit_code == code, result.output
    document = json.loads(result.stdout)
    assert document["ok"] is False
    assert document["error"]["code"] == code
    assert document["error"]["type"] == error_type
    assert message in document["error"]["message"]
    assert result.stdout.count("\n") == 1


def test_json_flag_before_leaf_command_is_global(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    result = _invoke_json(runner, ["--json", "json-contract-leaf"])

    _assert_success(result, None)


def test_literal_json_after_option_delimiter_stays_human_output(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    result = _invoke_json(
        runner,
        ["json-contract-literal", "--", "--json"],
    )

    assert result.exit_code == 0, result.output
    assert result.stdout == "--json\n"


def test_json_flag_after_leaf_command_is_inherited(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    result = _invoke_json(runner, ["json-contract-leaf", "--json"])

    _assert_success(result, None)


def test_json_flag_inside_nested_group_is_inherited(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    result = _invoke_json(
        runner,
        ["json-contract-group", "--json", "show"],
    )

    _assert_success(result, None)


def test_json_mode_serializes_command_return_value(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    result = _invoke_json(runner, ["--json", "json-contract-structured"])

    _assert_success(result, {"items": [1, 2]})


def test_json_mode_reserves_stdout_for_one_document(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    result = _invoke_json(runner, ["--json", "json-contract-diagnostics"])

    _assert_success(result, None)
    assert result.stdout.count("\n") == 1
    assert "\x1b[" not in result.stdout
    assert "plain diagnostic" not in result.stdout
    assert "rich diagnostic" not in result.stdout


def test_json_mode_routes_human_diagnostics_to_stderr(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    result = _invoke_json(runner, ["--json", "json-contract-diagnostics"])

    assert "plain diagnostic" in result.stderr
    assert "rich diagnostic" in result.stderr


def test_json_mode_structures_usage_errors(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    result = _invoke_json(runner, ["--json", "missing-json-command"])

    _assert_error(
        result,
        code=2,
        error_type="UsageError",
        message="No such command",
    )


def test_json_mode_structures_usecli_errors(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    result = _invoke_json(runner, ["--json", "json-contract-usecli-error"])

    _assert_error(
        result,
        code=1,
        error_type="UsecliError",
        message="framework failure",
    )


def test_json_mode_structures_unhandled_exceptions(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    result = _invoke_json(runner, ["--json", "json-contract-unhandled"])

    _assert_error(
        result,
        code=1,
        error_type="RuntimeError",
        message="unexpected failure",
    )
    assert "unexpected failure" in result.stderr
    assert "Traceback" not in result.stdout


def test_json_mode_preserves_explicit_nonzero_exit(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    result = _invoke_json(runner, ["--json", "json-contract-exit"])

    _assert_error(
        result,
        code=7,
        error_type="Exit",
        message="Command exited with status 7",
    )


def test_json_mode_structures_serialization_errors(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    result = _invoke_json(runner, ["--json", "json-contract-nonserializable"])

    _assert_error(
        result,
        code=1,
        error_type="JSONSerializationError",
        message="JSON serializable",
    )


def test_json_mode_rejects_interactive_selection(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    with patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command.run_interactive"
    ) as run_interactive:
        result = _invoke_json(
            runner,
            ["--json", "--interactive", "json-contract-leaf"],
        )

    _assert_error(
        result,
        code=2,
        error_type="NonInteractiveError",
        message="Interactive mode is unavailable",
    )
    run_interactive.assert_not_called()


def test_root_json_rejects_leaf_interactive_flag(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    with patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command.run_interactive"
    ) as run_interactive:
        result = _invoke_json(
            runner,
            ["--json", "json-contract-leaf", "--interactive"],
        )

    _assert_error(
        result,
        code=2,
        error_type="NonInteractiveError",
        message="Interactive mode is unavailable",
    )
    run_interactive.assert_not_called()


def test_root_json_rejects_nested_group_interactive_flag(
    runner: CliRunner,
    registered_json_commands: None,
) -> None:
    with patch(
        "usecli.cli.commands.defaults.base.internal.fzf_command.run_interactive"
    ) as run_interactive:
        result = _invoke_json(
            runner,
            [
                "--json",
                "json-contract-group",
                "--interactive",
                "show",
            ],
        )

    _assert_error(
        result,
        code=2,
        error_type="NonInteractiveError",
        message="Interactive mode is unavailable",
    )
    run_interactive.assert_not_called()
