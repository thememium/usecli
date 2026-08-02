"""Tests for usecli.menu — Menu component."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from usecli.cli.core.runtime import NonInteractiveError
from usecli.menu import Menu


class TestMenuSelect:
    @patch("usecli.menu.terminal_menu", return_value=["option_a"])
    def test_select_returns_first_item(self, mock_menu):
        result = Menu.select(["option_a", "option_b"], title="Pick one")
        assert result == "option_a"
        mock_menu.assert_called_once_with(
            ["option_a", "option_b"], title="Pick one", multi_select=False
        )

    @patch("usecli.menu.terminal_menu", return_value=[])
    def test_select_returns_none_when_cancelled(self, mock_menu):
        result = Menu.select(["option_a", "option_b"])
        assert result is None

    @patch("usecli.menu.is_json_mode", return_value=True)
    def test_select_raises_in_json_mode(self, mock_json):
        with pytest.raises(NonInteractiveError, match="menu"):
            Menu.select(["option_a"])


class TestMenuMultiSelect:
    @patch("usecli.menu.terminal_menu", return_value=["a", "c"])
    def test_multi_select_returns_selected_items(self, mock_menu):
        result = Menu.multi_select(["a", "b", "c"], title="Pick many")
        assert result == ["a", "c"]
        mock_menu.assert_called_once_with(
            ["a", "b", "c"], title="Pick many", multi_select=True
        )

    @patch("usecli.menu.terminal_menu", return_value=[])
    def test_multi_select_returns_empty_when_cancelled(self, mock_menu):
        result = Menu.multi_select(["a", "b"])
        assert result == []

    @patch("usecli.menu.is_json_mode", return_value=True)
    def test_multi_select_raises_in_json_mode(self, mock_json):
        with pytest.raises(NonInteractiveError, match="menu"):
            Menu.multi_select(["a"])
