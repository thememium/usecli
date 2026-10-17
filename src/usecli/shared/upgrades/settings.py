"""Upgrade source configuration from ``[usecli.upgrade]``.

The ``upgrade`` command discovers the install source from packaging
metadata by default. CLI authors distribute builds that metadata cannot
describe (private indexes, mirrors, Git remotes installed with a tool that
strips ``direct_url.json``), so the source can be pinned in
``usecli.config.toml``:

.. code-block:: toml

    [usecli.upgrade]
    enabled = true
    source = "auto"   # auto | pypi | git
    package = "my-cli"
    url = "https://github.com/owner/my-cli.git"   # source = "git"
    ref = "main"                                  # branch, tag, or commit

``auto`` keeps the metadata-based behaviour. Any other value is
authoritative: discovery, checks, and installation all use it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

UpgradeSource = Literal["auto", "pypi", "git"]

_SOURCES: dict[str, UpgradeSource] = {
    "auto": "auto",
    "pypi": "pypi",
    "git": "git",
}


@dataclass(frozen=True)
class UpgradeSettings:
    """Upgrade source overrides configured by the CLI author.

    Attributes:
        source: Where releases come from. ``auto`` derives it from the
            running installation's packaging metadata.
        package: Distribution name to upgrade. Defaults to the discovered
            distribution name.
        url: Git remote to upgrade from. Defaults to the discovered Git URL.
        ref: Git branch, tag, or commit to install. Defaults to the
            discovered revision.
    """

    source: UpgradeSource = "auto"
    package: str | None = None
    url: str | None = None
    ref: str | None = None

    @property
    def overrides_source(self) -> bool:
        """Whether the configured source replaces metadata discovery."""
        return self.source != "auto"


def _config_file(config: Any) -> str | None:
    path = getattr(config, "usecli_config_path", None)
    return str(path) if path else None


def config_error(message: str, suggestion: str, config: Any) -> Exception:
    # Imported lazily: exceptions live in the CLI layer and import Rich.
    from usecli.cli.core.exceptions.config import UsecliConfigError

    return UsecliConfigError(
        message,
        config_file=_config_file(config),
        suggestion=suggestion,
    )


def _text(value: Any) -> str | None:
    """Normalize an optional string setting; blank values mean unset."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def from_config(config: Any | None) -> UpgradeSettings:
    """Read ``[usecli.upgrade]`` settings from a ``ConfigManager``-like object.

    Args:
        config: Config manager exposing ``get(key, default)``. Objects
            without a ``get`` method (test doubles, ``None``) yield the
            defaults, preserving metadata-based discovery.

    Returns:
        The resolved settings.

    Raises:
        UsecliConfigError: When ``upgrade.source`` is not one of
            ``auto``, ``pypi``, or ``git``.
    """
    get = getattr(config, "get", None)
    if get is None:
        return UpgradeSettings()

    raw_source = get("upgrade.source", "auto")
    if raw_source is None:
        raw_source = "auto"
    if not isinstance(raw_source, str):
        raise config_error(
            f"upgrade.source must be a string, got {type(raw_source).__name__}.",
            'Set \\[usecli.upgrade] source = "auto", "pypi", or "git".',
            config,
        )
    source = _SOURCES.get(raw_source.strip().lower())
    if source is None:
        raise config_error(
            f"Invalid upgrade.source '{raw_source}'.",
            'Set \\[usecli.upgrade] source to "auto", "pypi", or "git".',
            config,
        )

    return UpgradeSettings(
        source=source,
        package=_text(get("upgrade.package")),
        url=_text(get("upgrade.url")),
        ref=_text(get("upgrade.ref")),
    )


__all__ = ["UpgradeSettings", "UpgradeSource", "config_error", "from_config"]
