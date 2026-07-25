"""Tests for JSON-mode runtime state and document serialization."""

from __future__ import annotations

import importlib
import importlib.util
from types import ModuleType

import pytest


def _runtime() -> ModuleType:
    """Import the runtime module after asserting the feature exists."""
    spec = importlib.util.find_spec("usecli.cli.core.runtime")
    assert spec is not None, "JSON runtime module has not been implemented"
    return importlib.import_module("usecli.cli.core.runtime")


def test_runtime_flags_default_to_disabled() -> None:
    runtime = _runtime()

    assert runtime.is_json_mode() is False
    assert runtime.is_quiet() is False


def test_runtime_context_sets_and_restores_flags() -> None:
    runtime = _runtime()

    with runtime.execution_context(json_mode=True, quiet=True):
        assert runtime.is_json_mode() is True
        assert runtime.is_quiet() is True

    assert runtime.is_json_mode() is False
    assert runtime.is_quiet() is False


def test_runtime_context_restores_nested_values() -> None:
    runtime = _runtime()

    with runtime.execution_context(json_mode=True):
        with runtime.execution_context(json_mode=False, quiet=True):
            assert runtime.is_json_mode() is False
            assert runtime.is_quiet() is True

        assert runtime.is_json_mode() is True
        assert runtime.is_quiet() is False


def test_success_document_has_stable_shape() -> None:
    runtime = _runtime()

    document = runtime.success_document({"items": [1, 2]})

    assert document == {"ok": True, "data": {"items": [1, 2]}}
    assert type(document["ok"]) is bool


def test_error_document_has_stable_shape() -> None:
    runtime = _runtime()

    document = runtime.error_document(
        error_type="UsageError",
        message="Invalid value",
        code=2,
    )

    assert document == {
        "ok": False,
        "error": {
            "type": "UsageError",
            "message": "Invalid value",
            "code": 2,
        },
    }
    assert type(document["ok"]) is bool
    assert type(document["error"]["type"]) is str
    assert type(document["error"]["message"]) is str
    assert type(document["error"]["code"]) is int


def test_serialize_document_is_unicode_safe_and_newline_terminated() -> None:
    runtime = _runtime()

    serialized = runtime.serialize_document(
        runtime.success_document({"message": "Errör 🚀"})
    )

    assert serialized.endswith("\n")
    assert serialized.count("\n") == 1
    assert "Errör 🚀" in serialized


def test_serialize_document_rejects_non_json_values() -> None:
    runtime = _runtime()
    serialization_error = getattr(runtime, "JSONSerializationError", None)
    assert serialization_error is not None, "JSONSerializationError is not defined"

    with pytest.raises(serialization_error, match="JSON serializable"):
        runtime.serialize_document(runtime.success_document({"invalid": {1, 2}}))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_serialize_document_rejects_non_finite_numbers(value: float) -> None:
    runtime = _runtime()

    with pytest.raises(runtime.JSONSerializationError, match="JSON serializable"):
        runtime.serialize_document(runtime.success_document(value))
