"""Tests for typer parameter compatibility shims."""

from __future__ import annotations

from click.exceptions import BadParameter

from usecli.cli.core._typer_compat import (
    _accept_click_ctx,
    make_argument,
    make_option,
)


def test_typer_argument_error_hint_accepts_click_context() -> None:
    argument = make_argument(param_decls=["name"])

    assert argument.get_error_hint(None) == "'name'"  # ty: ignore[too-many-positional-arguments]


def test_typer_option_error_hint_accepts_click_context() -> None:
    option = make_option(param_decls=["--env"])

    assert option.get_error_hint(None) == "'--env'"  # ty: ignore[too-many-positional-arguments]


def test_click_bad_parameter_formats_typer_argument_hint() -> None:
    argument = make_argument(param_decls=["name"])
    error = BadParameter("Missing parameter: name", param=argument)  # ty: ignore[invalid-argument-type]

    assert error.format_message() == (
        "Invalid value for 'name': Missing parameter: name"
    )


def test_accept_click_ctx_keeps_context_aware_methods() -> None:
    def get_error_hint(self, ctx=None):
        return "hint"

    assert _accept_click_ctx(get_error_hint) is get_error_hint
