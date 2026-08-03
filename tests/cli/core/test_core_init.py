"""Tests for usecli.cli.core — lazy import __getattr__."""

from __future__ import annotations

import pytest


class TestCoreLazyImports:
    def test_getattr_raises_for_unknown_attribute(self):
        import usecli.cli.core as core_mod

        with pytest.raises(AttributeError, match="has no attribute"):
            _ = core_mod.nonexistent_attribute_xyz

    def test_getattr_loads_COLOR(self):
        from usecli.cli.core import COLOR

        assert COLOR is not None

    def test_getattr_loads_UsecliError(self):
        from usecli.cli.core import UsecliError

        assert UsecliError is not None

    def test_getattr_loads_UsecliUsageError(self):
        from usecli.cli.core import UsecliUsageError

        assert UsecliUsageError is not None

    def test_getattr_loads_UsecliBadParameter(self):
        from usecli.cli.core import UsecliBadParameter

        assert UsecliBadParameter is not None

    def test_getattr_loads_UsecliConfigError(self):
        from usecli.cli.core import UsecliConfigError

        assert UsecliConfigError is not None

    def test_getattr_loads_UsecliValidationError(self):
        from usecli.cli.core import UsecliValidationError

        assert UsecliValidationError is not None

    def test_getattr_loads_ErrorHandler(self):
        from usecli.cli.core import ErrorHandler

        assert ErrorHandler is not None

    def test_getattr_loads_validate_not_empty(self):
        from usecli.cli.core import validate_not_empty

        assert callable(validate_not_empty)

    def test_getattr_loads_validate_command_name(self):
        from usecli.cli.core import validate_command_name

        assert callable(validate_command_name)

    def test_getattr_loads_validate_email(self):
        from usecli.cli.core import validate_email

        assert callable(validate_email)

    def test_getattr_loads_validate_url(self):
        from usecli.cli.core import validate_url

        assert callable(validate_url)

    def test_getattr_loads_validate_port(self):
        from usecli.cli.core import validate_port

        assert callable(validate_port)
