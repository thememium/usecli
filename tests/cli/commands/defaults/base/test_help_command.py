"""Tests for usecli.cli.commands.defaults.base.help_command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from usecli.cli.commands.defaults.base.help_command import HelpCommand


class TestHelpCommand:
    def test_signature(self):
        cmd = HelpCommand(MagicMock())
        assert cmd.signature() == "help"

    def test_description(self):
        cmd = HelpCommand(MagicMock())
        assert cmd.description() == "Show help information"

    @patch("usecli.cli.core.ui.list.list_commands")
    def test_handle_calls_list_commands(self, mock_list_commands):
        app = MagicMock()
        cmd = HelpCommand(app)
        cmd.handle()
        mock_list_commands.assert_called_once_with(app)
