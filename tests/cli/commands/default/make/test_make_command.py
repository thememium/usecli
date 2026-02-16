from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

import pytest

from usecli.cli.commands.defaults.make.make_command import MakeCommand


@pytest.fixture
def mock_typer_app():
    app = MagicMock()
    app.registered_commands = []
    app.command = Mock(return_value=lambda f: f)
    return app


@pytest.fixture
def make_command(mock_typer_app):
    return MakeCommand(app=mock_typer_app)


class TestMakeCommandSignature:
    def test_signature_returns_make_command(self, make_command):
        assert make_command.signature() == "make:command"

    def test_description_returns_string(self, make_command):
        description = make_command.description()
        assert isinstance(description, str)
        assert len(description) > 0


class TestMakeCommandVisible:
    def test_visible_returns_true_in_dev_mode(self, make_command):
        with patch(
            "usecli.cli.commands.defaults.make.make_command.get_config"
        ) as mock_get_config:
            mock_config = Mock()
            mock_config.is_dev.return_value = True
            mock_get_config.return_value = mock_config

            assert make_command.visible() is True

    def test_visible_returns_false_in_prod_mode(self, make_command):
        with patch(
            "usecli.cli.commands.defaults.make.make_command.get_config"
        ) as mock_get_config:
            mock_config = Mock()
            mock_config.is_dev.return_value = False
            mock_get_config.return_value = mock_config

            assert make_command.visible() is False

    def test_visible_checks_config_environment(self, make_command):
        with patch(
            "usecli.cli.commands.defaults.make.make_command.get_config"
        ) as mock_get_config:
            mock_config = Mock()
            mock_config.is_dev.return_value = True
            mock_get_config.return_value = mock_config

            make_command.visible()
            mock_config.is_dev.assert_called_once()
