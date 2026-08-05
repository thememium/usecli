"""Tests for usecli.cli.commands.defaults.make.make_bundle_command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from usecli.cli.commands.defaults.make.make_bundle_command import (
    MakeBundleCommand,
    _pyinstaller_available,
)
from usecli.shared.config.manager import reset_config


@pytest.fixture
def mock_typer_app():
    app = MagicMock()
    app.registered_commands = []
    app.command = MagicMock(return_value=lambda f: f)
    return app


@pytest.fixture
def make_bundle_command(mock_typer_app):
    return MakeBundleCommand(app=mock_typer_app)


@pytest.fixture(autouse=True)
def reset_usecli_config():
    reset_config()
    yield
    reset_config()


class TestPyinstallerAvailable:
    def test_true_when_installed(self):
        # PyInstaller is installed in the test environment.
        assert _pyinstaller_available() is True

    @patch(
        "usecli.cli.commands.defaults.make.make_bundle_command.importlib.util.find_spec"
    )
    def test_false_when_missing(self, mock_find_spec):
        mock_find_spec.return_value = None
        assert _pyinstaller_available() is False
        mock_find_spec.assert_called_once_with("PyInstaller")


class TestMakeBundleCommandSignature:
    def test_signature(self, make_bundle_command):
        assert make_bundle_command.signature() == "make:bundle"

    def test_description(self, make_bundle_command):
        assert isinstance(make_bundle_command.description(), str)
        assert make_bundle_command.description().strip()


class TestMakeBundleCommandVisibility:
    @patch("usecli.cli.commands.defaults.make.make_bundle_command.sys")
    @patch("usecli.cli.commands.defaults.make.make_bundle_command.os")
    @patch(
        "usecli.cli.commands.defaults.make.make_bundle_command._pyinstaller_available"
    )
    def test_visible_when_usecli_and_pyinstaller(
        self, mock_available, mock_os, mock_sys, make_bundle_command
    ):
        mock_available.return_value = True
        mock_sys.argv = ["/usr/bin/usecli"]
        mock_os.path.basename.return_value = "usecli"
        assert make_bundle_command.visible() is True

    @patch("usecli.cli.commands.defaults.make.make_bundle_command.sys")
    @patch("usecli.cli.commands.defaults.make.make_bundle_command.os")
    @patch(
        "usecli.cli.commands.defaults.make.make_bundle_command._pyinstaller_available"
    )
    def test_not_visible_when_not_usecli(
        self, mock_available, mock_os, mock_sys, make_bundle_command
    ):
        mock_available.return_value = True
        mock_sys.argv = ["/usr/bin/magic"]
        mock_os.path.basename.return_value = "magic"
        assert make_bundle_command.visible() is False

    @patch("usecli.cli.commands.defaults.make.make_bundle_command.sys")
    @patch("usecli.cli.commands.defaults.make.make_bundle_command.os")
    @patch(
        "usecli.cli.commands.defaults.make.make_bundle_command._pyinstaller_available"
    )
    def test_not_visible_without_pyinstaller(
        self, mock_available, mock_os, mock_sys, make_bundle_command
    ):
        mock_available.return_value = False
        mock_sys.argv = ["/usr/bin/usecli"]
        mock_os.path.basename.return_value = "usecli"
        assert make_bundle_command.visible() is False


class TestMakeBundleCommandHandle:
    @patch(
        "usecli.cli.commands.defaults.make.make_bundle_command._pyinstaller_available"
    )
    def test_invokes_pyinstaller_with_defaults(
        self, mock_available, make_bundle_command
    ):
        mock_available.return_value = True
        with patch("usecli.bundler.pyinstaller") as mock_pyi:
            make_bundle_command.handle(yes=True)
        mock_pyi.assert_called_once_with(
            config_path=None,
            mode="onefile",
            name=None,
            distpath=None,
            workpath=None,
        )

    @patch(
        "usecli.cli.commands.defaults.make.make_bundle_command._pyinstaller_available"
    )
    def test_invokes_pyinstaller_with_args(
        self, mock_available, make_bundle_command, tmp_path
    ):
        mock_available.return_value = True
        config = tmp_path / "cli" / "usecli.config.toml"
        with patch("usecli.bundler.pyinstaller") as mock_pyi:
            make_bundle_command.handle(
                str(config),
                mode="onedir",
                name="app",
                distpath=str(tmp_path / "out"),
                workpath=str(tmp_path / "work"),
                yes=True,
            )
        mock_pyi.assert_called_once_with(
            config_path=str(config),
            mode="onedir",
            name="app",
            distpath=str(tmp_path / "out"),
            workpath=str(tmp_path / "work"),
        )

    @patch(
        "usecli.cli.commands.defaults.make.make_bundle_command._pyinstaller_available"
    )
    def test_missing_pyinstaller_prints_help(self, mock_available, make_bundle_command):
        mock_available.return_value = False
        with (
            patch("usecli.bundler.pyinstaller") as mock_pyi,
            patch(
                "usecli.cli.commands.defaults.make.make_bundle_command.console"
            ) as mock_console,
        ):
            make_bundle_command.handle()
        mock_pyi.assert_not_called()
        mock_console.print.assert_called_once()

    @patch(
        "usecli.cli.commands.defaults.make.make_bundle_command._pyinstaller_available"
    )
    def test_invalid_mode_prints_error(self, mock_available, make_bundle_command):
        mock_available.return_value = True
        with (
            patch("usecli.bundler.pyinstaller") as mock_pyi,
            patch(
                "usecli.cli.commands.defaults.make.make_bundle_command.console"
            ) as mock_console,
        ):
            make_bundle_command.handle(mode="bogus")
        mock_pyi.assert_not_called()
        mock_console.print.assert_called_once()


class TestMakeBundleCommandConfirmation:
    CONFIRM_MOD = "usecli.cli.commands.defaults.make.make_bundle_command.Confirm"
    AVAIL_MOD = (
        "usecli.cli.commands.defaults.make.make_bundle_command._pyinstaller_available"
    )

    @patch(AVAIL_MOD)
    @patch(CONFIRM_MOD)
    def test_aborts_when_not_confirmed(
        self, mock_confirm, mock_available, make_bundle_command
    ):
        mock_available.return_value = True
        mock_confirm.ask.return_value = False
        with patch("usecli.bundler.pyinstaller") as mock_pyi:
            make_bundle_command.handle()
        mock_pyi.assert_not_called()

    @patch(AVAIL_MOD)
    @patch(CONFIRM_MOD)
    def test_creates_when_confirmed(
        self, mock_confirm, mock_available, make_bundle_command
    ):
        mock_available.return_value = True
        mock_confirm.ask.return_value = True
        with patch("usecli.bundler.pyinstaller") as mock_pyi:
            make_bundle_command.handle()
        mock_pyi.assert_called_once()

    @patch(AVAIL_MOD)
    @patch(CONFIRM_MOD)
    def test_confirmation_defaults_to_no(
        self, mock_confirm, mock_available, make_bundle_command
    ):
        mock_available.return_value = True
        mock_confirm.ask.return_value = False
        with patch("usecli.bundler.pyinstaller") as mock_pyi:
            make_bundle_command.handle()
        mock_pyi.assert_not_called()
        mock_confirm.ask.assert_called_once()
        assert mock_confirm.ask.call_args.kwargs["default"] is False

    @patch(AVAIL_MOD)
    @patch(CONFIRM_MOD)
    def test_yes_skips_prompt(self, mock_confirm, mock_available, make_bundle_command):
        mock_available.return_value = True
        with patch("usecli.bundler.pyinstaller") as mock_pyi:
            make_bundle_command.handle(yes=True)
        mock_confirm.ask.assert_not_called()
        mock_pyi.assert_called_once()
