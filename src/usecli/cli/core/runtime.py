"""Execution state and structured output helpers for usecli."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar

_JSON_MODE: ContextVar[bool] = ContextVar("usecli_json_mode", default=False)
_QUIET: ContextVar[bool] = ContextVar("usecli_quiet", default=False)


class JSONSerializationError(TypeError):
    """Raised when a command result cannot be represented as JSON."""


class InvocationExit(Exception):
    """Preserve an explicit command exit before Click converts it to a value."""

    def __init__(self, code: int) -> None:
        super().__init__(f"Command exited with status {code}")
        self.code = code


class NonInteractiveError(RuntimeError):
    """Raised when an interactive operation cannot run in JSON mode."""

    code = 2


def is_json_mode() -> bool:
    """Return whether the current invocation uses structured JSON output."""
    return _JSON_MODE.get()


def is_quiet() -> bool:
    """Return whether the current invocation suppresses human-facing output."""
    return _QUIET.get()


@contextmanager
def execution_context(
    *,
    json_mode: bool | None = None,
    quiet: bool | None = None,
) -> Iterator[None]:
    """Temporarily set invocation flags and restore their previous values."""
    json_token = _JSON_MODE.set(json_mode) if json_mode is not None else None
    quiet_token = _QUIET.set(quiet) if quiet is not None else None
    try:
        yield
    finally:
        if quiet_token is not None:
            _QUIET.reset(quiet_token)
        if json_token is not None:
            _JSON_MODE.reset(json_token)


def success_document(data: object = None) -> dict[str, object]:
    """Build the stable document emitted for a successful invocation."""
    return {"ok": True, "data": data}


def error_document(
    *,
    error_type: str,
    message: str,
    code: int,
) -> dict[str, object]:
    """Build the stable document emitted for a failed invocation."""
    return {
        "ok": False,
        "error": {
            "type": error_type,
            "message": message,
            "code": code,
        },
    }


def serialize_document(document: Mapping[str, object]) -> str:
    """Serialize one JSON document with UTF-8 text and a trailing newline."""
    try:
        return (
            json.dumps(
                document,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            + "\n"
        )
    except (TypeError, ValueError) as error:
        raise JSONSerializationError(
            "Command result must be JSON serializable"
        ) from error
