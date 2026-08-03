"""Coverage-focused tests for usecli.cli.utils.interactive.terminal_menu.

Targets uncovered lines without modifying source:

- line 22: ``_apply_safe_search_len_patch`` is idempotent (already applied)
- lines 25-29: the patched ``Search.__len__`` safe search-length helper
- line 39: ``_apply_vim_page_keys_patch`` is idempotent (already applied)
- lines 48-61: the patched ``_read_next_key`` vim page-key translation

No real terminal is used; ``os.read`` and menu attributes are mocked.
"""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

# NOTE: `import usecli.cli.utils.interactive.terminal_menu as tm` would bind the
# `terminal_menu` *function* (re-exported by the package __init__), so we import
# the module object explicitly.
tm = importlib.import_module("usecli.cli.utils.interactive.terminal_menu")


class TestSafeSearchLenPatch:
    def test_patch_is_idempotent(self):
        """Calling the patch again returns immediately (line 22)."""
        tm._apply_safe_search_len_patch()

    def test_search_len_with_text(self):
        """len() on a Search with text returns the display width (lines 28-29)."""
        search = tm.TerminalMenu.Search(["a", "b"], search_text="abc")
        assert len(search) == 3

    def test_search_len_with_none(self):
        """len() on a Search with no text returns 0 (line 27)."""
        search = tm.TerminalMenu.Search(["a", "b"])
        assert len(search) == 0


class TestVimPageKeysPatch:
    def test_patch_is_idempotent(self):
        """Calling the patch again returns immediately (line 39)."""
        tm._apply_vim_page_keys_patch()

    def _make_menu(self, search=False, search_key="/"):
        menu = MagicMock()
        menu._terminal_code_to_codename = {}
        menu._tty_in = MagicMock()
        menu._tty_in.fileno.return_value = 0
        menu._reading_next_key = False
        menu._paint_before_next_read = False
        menu._paint_menu = MagicMock()
        menu._search = search
        menu._search_key = search_key
        return menu

    def _call(self, menu, key_bytes, ignore_case=True):
        with patch("simple_term_menu.os.read", return_value=key_bytes):
            return tm.TerminalMenu._read_next_key(menu, ignore_case)

    def test_d_maps_to_page_down(self):
        menu = self._make_menu()
        assert self._call(menu, b"d") == "page_down"

    def test_u_maps_to_page_up(self):
        menu = self._make_menu()
        assert self._call(menu, b"u") == "page_up"

    def test_uppercase_j_maps_to_down(self):
        menu = self._make_menu()
        assert self._call(menu, b"J", ignore_case=False) == "down"

    def test_uppercase_k_maps_to_up(self):
        menu = self._make_menu()
        assert self._call(menu, b"K", ignore_case=False) == "up"

    def test_other_key_returned_unchanged(self):
        menu = self._make_menu()
        assert self._call(menu, b"x") == "x"

    def test_search_active_returns_key_unchanged(self):
        menu = self._make_menu(search=True)
        assert self._call(menu, b"d") == "d"

    def test_no_search_key_returns_key_unchanged(self):
        menu = self._make_menu(search_key=None)
        assert self._call(menu, b"d") == "d"
