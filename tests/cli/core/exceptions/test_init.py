"""Tests for usecli.cli.core.exceptions — lazy import __getattr__."""

from __future__ import annotations

import pytest


class TestExceptionsLazyImports:
    def test_getattr_raises_for_unknown_attribute(self):
        import usecli.cli.core.exceptions as exc_mod

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = exc_mod.nonexistent_exception_12345

    def test_getattr_loads_UsecliError(self):
        from usecli.cli.core.exceptions import UsecliError

        assert UsecliError is not None

    def test_getattr_loads_UsecliUsageError(self):
        from usecli.cli.core.exceptions import UsecliUsageError

        assert UsecliUsageError is not None

    def test_getattr_loads_UsecliBadParameter(self):
        from usecli.cli.core.exceptions import UsecliBadParameter

        assert UsecliBadParameter is not None

    def test_getattr_loads_UsecliConfigError(self):
        from usecli.cli.core.exceptions import UsecliConfigError

        assert UsecliConfigError is not None

    def test_getattr_loads_UsecliValidationError(self):
        from usecli.cli.core.exceptions import UsecliValidationError

        assert UsecliValidationError is not None
