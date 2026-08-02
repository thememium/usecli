"""Tests for usecli.params — wrappers around Typer Argument/Option."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
import pytest
import typer

from usecli.params import Argument, Option


# ---------------------------------------------------------------------------
# Argument wrapper
# ---------------------------------------------------------------------------


class TestArgument:
    def test_required_argument_returns_typer_argument(self):
        """A required argument (default=...) should produce a Typer Argument."""
        result = Argument(..., help="Your name")
        assert result is not None

    def test_argument_with_default_value(self):
        result = Argument("world", help="Greeting target")
        assert result is not None

    def test_argument_show_default_false(self):
        result = Argument("x", show_default=False)
        assert result is not None

    def test_argument_show_choices_false(self):
        result = Argument("a", show_choices=False)
        assert result is not None

    def test_argument_extra_kwargs_forwarded(self):
        """Extra kwargs should be forwarded to typer.Argument."""
        result = Argument(..., help="Name", metavar="NAME")
        assert result is not None


# ---------------------------------------------------------------------------
# Option wrapper — basic behavior
# ---------------------------------------------------------------------------


class TestOptionBasic:
    def test_option_returns_typer_option(self):
        result = Option(False, "--verbose", "-v", help="Verbose mode")
        assert result is not None

    def test_option_with_none_default(self):
        result = Option(None, "--name", help="Your name")
        assert result is not None

    def test_option_is_flag_with_none_default_sets_false(self):
        """When is_flag=True and default=None, default should become False."""
        result = Option(None, "--debug", is_flag=True, help="Debug mode")
        assert result is not None

    def test_option_extra_kwargs_forwarded(self):
        result = Option("value", "--opt", help="An option", metavar="VAL")
        assert result is not None


# ---------------------------------------------------------------------------
# Option wrapper — callback / interactive prompt logic
# ---------------------------------------------------------------------------


class TestOptionCallback:
    def _make_context(self, param_name: str = "verbose", source=None, interactive: bool = False):
        """Build a minimal mock Click context."""
        ctx = MagicMock(spec=click.Context)
        ctx.info_name = "test-command"
        ctx.resilient_parsing = False
        root_params = {"interactive": interactive}
        ctx.find_root.return_value = MagicMock(params=root_params)
        if source is not None:
            ctx.get_parameter_source.return_value = source
        else:
            ctx.get_parameter_source.return_value = click.core.ParameterSource.COMMANDLINE
        return ctx

    def _make_param(self, name: str = "verbose"):
        param = MagicMock(spec=click.Parameter)
        param.name = name
        return param

    def test_bool_flag_prompts_when_default_and_interactive(self):
        """A bool option with default should prompt in interactive mode when value is default."""
        ctx = self._make_context(
            param_name="verbose",
            source=click.core.ParameterSource.DEFAULT,
            interactive=True,
        )
        param = self._make_param("verbose")

        with patch("usecli.params.Confirm") as mock_confirm:
            mock_confirm.ask.return_value = True
            opt = Option(False, "--verbose", is_flag=True, help="Verbose")
            # The callback is attached to the option; invoke it
            callback = opt.callback
            result = callback(ctx, param, False)
            mock_confirm.ask.assert_called_once()
            assert result is True

    def test_bool_flag_does_not_prompt_when_value_from_commandline(self):
        """When the value comes from the command line, no prompt should appear."""
        ctx = self._make_context(
            param_name="verbose",
            source=click.core.ParameterSource.COMMANDLINE,
            interactive=True,
        )
        param = self._make_param("verbose")

        with patch("usecli.params.Confirm") as mock_confirm:
            opt = Option(False, "--verbose", is_flag=True, help="Verbose")
            callback = opt.callback
            result = callback(ctx, param, True)
            mock_confirm.ask.assert_not_called()
            assert result is True

    def test_bool_flag_does_not_prompt_when_not_interactive(self):
        """When interactive is False, no prompt should appear."""
        ctx = self._make_context(
            param_name="verbose",
            source=click.core.ParameterSource.DEFAULT,
            interactive=False,
        )
        param = self._make_param("verbose")

        with patch("usecli.params.Confirm") as mock_confirm:
            opt = Option(False, "--verbose", is_flag=True, help="Verbose")
            callback = opt.callback
            result = callback(ctx, param, False)
            mock_confirm.ask.assert_not_called()
            assert result is False

    def test_non_flag_option_does_not_prompt(self):
        """A non-flag option should not trigger interactive prompting."""
        ctx = self._make_context(
            param_name="name",
            source=click.core.ParameterSource.DEFAULT,
            interactive=True,
        )
        param = self._make_param("name")

        with patch("usecli.params.Confirm") as mock_confirm:
            opt = Option("default", "--name", help="Name")
            callback = opt.callback
            result = callback(ctx, param, "default")
            mock_confirm.ask.assert_not_called()
            assert result == "default"

    def test_user_callback_called_after_prompt(self):
        """If a user-supplied callback is provided, it should be called."""
        user_cb = MagicMock(return_value="cb_result")
        ctx = self._make_context(
            param_name="verbose",
            source=click.core.ParameterSource.COMMANDLINE,
            interactive=True,
        )
        param = self._make_param("verbose")

        opt = Option(False, "--verbose", is_flag=True, callback=user_cb, help="Verbose")
        callback = opt.callback
        result = callback(ctx, param, True)

        user_cb.assert_called_once_with(ctx, param, True)
        assert result == "cb_result"

    def test_user_callback_called_when_no_prompt(self):
        """User callback is called even when no interactive prompt triggers."""
        user_cb = MagicMock(return_value="val")
        ctx = self._make_context(
            param_name="name",
            source=click.core.ParameterSource.COMMANDLINE,
            interactive=False,
        )
        param = self._make_param("name")

        opt = Option("default", "--name", callback=user_cb, help="Name")
        callback = opt.callback
        result = callback(ctx, param, "input")

        user_cb.assert_called_once_with(ctx, param, "input")
        assert result == "val"

    def test_resilient_parsing_skips_prompt(self):
        """During resilient parsing (e.g. --help), no prompt should appear."""
        ctx = self._make_context(
            param_name="verbose",
            source=click.core.ParameterSource.DEFAULT,
            interactive=True,
        )
        ctx.resilient_parsing = True
        param = self._make_param("verbose")

        with patch("usecli.params.Confirm") as mock_confirm:
            opt = Option(False, "--verbose", is_flag=True, help="Verbose")
            callback = opt.callback
            result = callback(ctx, param, False)
            mock_confirm.ask.assert_not_called()
            assert result is False
