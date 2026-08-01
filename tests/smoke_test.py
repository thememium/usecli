from __future__ import annotations

from importlib import resources

from click.testing import CliRunner
from typer.main import get_command

import usecli


def _assert_resource(relative_path: str) -> None:
    root = resources.files("usecli")
    target = root.joinpath(relative_path)
    if not target.is_file():
        raise AssertionError(f"Missing packaged resource: {relative_path}")


def _assert_basic_imports() -> None:
    from usecli import (
        Argument,
        BaseCommand,
        Confirm,
        Console,
        Menu,
        Option,
        ProgressBar,
        Prompt,
        Spinner,
        console,
        main,
    )

    assert BaseCommand is not None
    assert Console is not None
    assert Menu is not None
    assert Prompt is not None
    assert Confirm is not None
    assert Argument is not None
    assert Option is not None
    assert Spinner is not None
    assert ProgressBar is not None
    assert console is not None
    assert callable(main)


def _assert_packaged_files() -> None:
    _assert_resource("cli/templates/usecli.config.toml.j2")
    _assert_resource("cli/templates/theme.toml.j2")
    _assert_resource("cli/templates/command.py.j2")
    _assert_resource("cli/themes/default.toml")
    _assert_resource("cli/commands/defaults/base/help_command.py")
    _assert_resource("cli/commands/defaults/make/make_command.py")


def _assert_cli_runs() -> None:
    runner = CliRunner()

    command = get_command(usecli.app)

    result = runner.invoke(command, ["--version"])
    assert result.exit_code == 0, result.output

    result = runner.invoke(command, ["--help"])
    assert result.exit_code == 0, result.output


def main() -> None:
    _assert_basic_imports()
    _assert_packaged_files()
    _assert_cli_runs()


if __name__ == "__main__":
    main()
