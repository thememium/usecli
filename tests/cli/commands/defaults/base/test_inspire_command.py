"""Tests for usecli.cli.commands.defaults.base.inspire_command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from usecli.cli.commands.defaults.base.inspire_command import InspireCommand


class TestInspireCommand:
    def _make_command(self):
        app = MagicMock()
        return InspireCommand(app)

    def test_signature(self):
        cmd = self._make_command()
        assert cmd.signature() == "inspire"

    def test_description(self):
        cmd = self._make_command()
        assert cmd.description() == "Show a random inspirational quote"

    @patch("usecli.cli.commands.defaults.base.inspire_command.get_config")
    def test_visible_when_not_hidden(self, mock_get_config):
        mock_get_config.return_value = MagicMock(get=MagicMock(return_value=False))
        cmd = self._make_command()
        assert cmd.visible() is True

    @patch("usecli.cli.commands.defaults.base.inspire_command.get_config")
    def test_not_visible_when_hidden(self, mock_get_config):
        mock_get_config.return_value = MagicMock(get=MagicMock(return_value=True))
        cmd = self._make_command()
        assert cmd.visible() is False

    @patch("usecli.cli.core.runtime.is_json_mode", return_value=True)
    @patch("usecli.cli.commands.defaults.base.inspire_command.get_config")
    def test_handle_json_mode_returns_data(self, mock_get_config, mock_json):
        mock_get_config.return_value = MagicMock(get=MagicMock(return_value=False))
        cmd = self._make_command()
        result = cmd.handle()

        assert "quote" in result
        assert "author" in result
        assert isinstance(result["quote"], str)
        assert isinstance(result["author"], str)
        assert len(result["quote"]) > 0
        assert len(result["author"]) > 0

    @patch("usecli.cli.core.runtime.is_json_mode", return_value=False)
    @patch("usecli.cli.commands.defaults.base.inspire_command.get_config")
    @patch("rich.console.Console")
    @patch("rich.panel.Panel")
    def test_handle_prints_panel_in_normal_mode(
        self, mock_panel, mock_console_cls, mock_get_config, mock_json
    ):
        mock_get_config.return_value = MagicMock(get=MagicMock(return_value=False))
        mock_console_instance = MagicMock()
        mock_console_cls.return_value = mock_console_instance

        cmd = self._make_command()
        result = cmd.handle()

        assert "quote" in result
        assert "author" in result
        mock_console_instance.print.assert_called_once()

    @patch("usecli.cli.core.runtime.is_json_mode", return_value=True)
    @patch("usecli.cli.commands.defaults.base.inspire_command.get_config")
    def test_handle_selects_from_quotes_list(self, mock_get_config, mock_json):
        mock_get_config.return_value = MagicMock(get=MagicMock(return_value=False))
        cmd = self._make_command()

        results = set()
        for _ in range(20):
            result = cmd.handle()
            results.add(result["author"])

        assert len(results) > 1

    @patch("usecli.cli.core.runtime.is_json_mode", return_value=True)
    @patch("usecli.cli.commands.defaults.base.inspire_command.get_config")
    def test_handle_quote_contains_dash_separator(self, mock_get_config, mock_json):
        mock_get_config.return_value = MagicMock(get=MagicMock(return_value=False))
        cmd = self._make_command()
        result = cmd.handle()

        assert result["quote"] != ""
        assert result["author"] != ""
        assert " - " not in result["author"]
