"""Tests for usecli progress indicators."""

from __future__ import annotations

import importlib
import importlib.util
from contextlib import redirect_stdout
from io import StringIO
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console as RichConsole

import usecli
from usecli.cli.config.colors import COLOR
from usecli.cli.core.runtime import execution_context


def _progress_module() -> ModuleType:
    spec = importlib.util.find_spec("usecli.progress")
    assert spec is not None, "Progress helpers have not been implemented"
    return importlib.import_module("usecli.progress")


def _mock_console(*, interactive: bool) -> MagicMock:
    return MagicMock(is_terminal=interactive, is_interactive=interactive)


def test_progress_helpers_are_public_package_exports() -> None:
    progress_module = _progress_module()

    assert usecli.Spinner is progress_module.Spinner
    assert usecli.ProgressBar is progress_module.ProgressBar


def test_spinner_uses_stderr_progress_without_stream_redirection() -> None:
    progress_module = _progress_module()
    console = _mock_console(interactive=True)
    rich_progress = MagicMock()
    rich_progress.add_task.return_value = 42

    with (
        patch.object(progress_module, "Console", return_value=console) as console_type,
        patch.object(
            progress_module,
            "Progress",
            return_value=rich_progress,
        ) as progress_type,
    ):
        with progress_module.Spinner("Loading") as spinner:
            spinner.update("Still loading")

    console_type.assert_called_once_with(stderr=True)
    assert progress_type.call_args.kwargs == {
        "console": console,
        "disable": False,
        "redirect_stdout": False,
        "redirect_stderr": False,
        "transient": True,
    }
    rich_progress.__enter__.assert_called_once_with()
    rich_progress.add_task.assert_called_once_with("Loading", total=None)
    rich_progress.update.assert_called_once_with(42, description="Still loading")
    rich_progress.__exit__.assert_called_once_with(None, None, None)


def test_progress_bar_uses_stderr_progress_and_advances_one_task() -> None:
    progress_module = _progress_module()
    console = _mock_console(interactive=True)
    rich_progress = MagicMock()
    rich_progress.add_task.return_value = 42

    with (
        patch.object(progress_module, "Console", return_value=console) as console_type,
        patch.object(
            progress_module,
            "Progress",
            return_value=rich_progress,
        ) as progress_type,
    ):
        with progress_module.ProgressBar(total=3, description="Processing") as progress:
            progress.advance()
            progress.update(completed=2, description="Almost done")

    console_type.assert_called_once_with(stderr=True)
    assert progress_type.call_args.kwargs == {
        "console": console,
        "disable": False,
        "redirect_stdout": False,
        "redirect_stderr": False,
    }
    rich_progress.__enter__.assert_called_once_with()
    rich_progress.add_task.assert_called_once_with("Processing", total=3)
    rich_progress.advance.assert_called_once_with(42, 1)
    rich_progress.update.assert_called_once_with(
        42,
        completed=2,
        description="Almost done",
    )
    rich_progress.__exit__.assert_called_once_with(None, None, None)


@pytest.mark.parametrize(
    ("json_mode", "quiet", "is_interactive"),
    [
        (True, False, True),
        (False, True, True),
        (False, False, False),
    ],
)
def test_spinner_uses_rich_disable_but_keeps_state(
    json_mode: bool,
    quiet: bool,
    is_interactive: bool,
) -> None:
    progress_module = _progress_module()
    console = _mock_console(interactive=is_interactive)
    # A dumb terminal may still report is_terminal=True; is_interactive is authoritative.
    if not is_interactive:
        console.is_terminal = True
    rich_progress = MagicMock()
    rich_progress.add_task.return_value = 1

    with (
        execution_context(json_mode=json_mode),
        patch.object(progress_module, "Console", return_value=console),
        patch.object(
            progress_module,
            "Progress",
            return_value=rich_progress,
        ) as progress_type,
        progress_module.Spinner("Loading", quiet=quiet) as spinner,
    ):
        spinner.update("Still loading")

    assert progress_type.call_args.kwargs["disable"] is True
    rich_progress.add_task.assert_called_once_with("Loading", total=None)
    rich_progress.update.assert_called_once_with(1, description="Still loading")
    assert spinner.message == "Still loading"


@pytest.mark.parametrize(
    ("json_mode", "quiet", "is_interactive"),
    [
        (True, False, True),
        (False, True, True),
        (False, False, False),
    ],
)
def test_progress_bar_uses_rich_disable_but_tracks_state(
    json_mode: bool,
    quiet: bool,
    is_interactive: bool,
) -> None:
    progress_module = _progress_module()
    console = _mock_console(interactive=is_interactive)
    if not is_interactive:
        console.is_terminal = True
    rich_progress = MagicMock()
    rich_progress.add_task.return_value = 1

    with (
        execution_context(json_mode=json_mode),
        patch.object(progress_module, "Console", return_value=console),
        patch.object(
            progress_module,
            "Progress",
            return_value=rich_progress,
        ) as progress_type,
        progress_module.ProgressBar(
            total=3,
            description="Processing",
            quiet=quiet,
        ) as progress,
    ):
        progress.advance()
        progress.update(completed=2, description="Almost done")

    assert progress_type.call_args.kwargs["disable"] is True
    rich_progress.advance.assert_called_once_with(1, 1)
    rich_progress.update.assert_called_once_with(
        1,
        completed=2,
        description="Almost done",
    )
    assert progress.completed == 2
    assert progress.description == "Almost done"


def test_spinner_preserves_command_stdout_while_rendering() -> None:
    progress_module = _progress_module()
    stdout = StringIO()
    stderr = StringIO()
    console = RichConsole(file=stderr, force_terminal=True, width=80)

    with (
        patch.object(progress_module, "Console", return_value=console),
        redirect_stdout(stdout),
        progress_module.Spinner("Loading"),
    ):
        print("machine payload")

    assert stdout.getvalue() == "machine payload\n"
    assert "machine payload" not in stderr.getvalue()


def test_spinner_uses_active_theme_styles() -> None:
    progress_module = _progress_module()
    console = _mock_console(interactive=True)
    rich_progress = MagicMock()
    rich_progress.add_task.return_value = 1

    with (
        patch.object(progress_module, "Console", return_value=console),
        patch.object(
            progress_module, "Progress", return_value=rich_progress
        ) as progress_type,
        progress_module.Spinner("Loading"),
    ):
        pass

    columns = progress_type.call_args.args
    column_configuration = repr([vars(column) for column in columns])
    assert COLOR.INFO in column_configuration
    assert COLOR.PRIMARY in column_configuration


def test_progress_bar_columns_use_active_theme_styles() -> None:
    progress_module = _progress_module()
    console = _mock_console(interactive=True)
    rich_progress = MagicMock()
    rich_progress.add_task.return_value = 1

    with (
        patch.object(progress_module, "Console", return_value=console),
        patch.object(
            progress_module, "Progress", return_value=rich_progress
        ) as progress_type,
        progress_module.ProgressBar(total=1),
    ):
        pass

    columns = progress_type.call_args.args
    column_configuration = repr([vars(column) for column in columns])
    assert COLOR.INFO in column_configuration
    assert COLOR.PRIMARY in column_configuration
    assert COLOR.SUCCESS in column_configuration
    assert COLOR.FOREGROUND_MUTED in column_configuration
