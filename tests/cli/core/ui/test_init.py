"""Tests for usecli.cli.core.ui — lazy import __getattr__."""

from __future__ import annotations

import pytest


class TestUiLazyImports:
    def test_getattr_raises_for_unknown_attribute(self):
        import usecli.cli.core.ui as ui_mod

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = ui_mod.nonexistent_attribute_12345

    def test_getattr_loads_COLOR(self):
        import usecli.cli.core.ui as ui_mod

        color = ui_mod.COLOR
        assert color is not None

    def test_getattr_loads_bold(self):
        import usecli.cli.core.ui as ui_mod

        bold = ui_mod.bold
        assert callable(bold)

    def test_getattr_loads_style(self):
        import usecli.cli.core.ui as ui_mod

        style = ui_mod.style
        assert callable(style)

    def test_getattr_loads_list_commands(self):
        import usecli.cli.core.ui as ui_mod

        lc = ui_mod.list_commands
        assert callable(lc)

    def test_getattr_loads_print_title(self):
        import usecli.cli.core.ui as ui_mod

        pt = ui_mod.print_title
        assert callable(pt)

    def test_getattr_loads_get_project_name(self):
        import usecli.cli.core.ui as ui_mod

        gpn = ui_mod.get_project_name
        assert callable(gpn)
