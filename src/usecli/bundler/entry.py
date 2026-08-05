"""Runtime entry point for usecli projects.

This module is the analysis target for the single-file bundles produced by
:func:`usecli.pyinstaller` and, in development, the shared runtime behind a
project's ``main.py`` (``from usecli.bundler.entry import main``). It works in
**both** modes:

* **Frozen** (PyInstaller): points usecli's global
  :class:`~usecli.shared.config.manager.ConfigManager` at the project assets
  (``usecli.config.toml``, ``commands/``, ``templates/``, ``themes/``,
  ``pyproject.toml``) dropped under ``sys._MEIPASS/<BUNDLE_DATA_DIR>`` — without
  any CWD / ``rglob`` filesystem discovery.
* **Development** (``uv run main.py``): locates the same assets from the source
  tree (via the project-root bounded search) and injects them explicitly, so no
  PyInstaller install is required.

In both modes it also keeps the CLI resolvable on PATH so the interactive (fzf)
runner's shell-outs (``/bin/sh -c "magic magic hello"``) succeed even though the
binary is never installed on PATH.

The PyInstaller spec (``--collect-all usecli``) bundles every usecli module, so
the lazy imports below are always available at runtime.
"""

from __future__ import annotations

import os
import stat
import sys
import tempfile
from pathlib import Path

# Subdirectory (under sys._MEIPASS) where the spec drops the project assets.
# The spec builder imports this constant so the runtime and the build agree.
BUNDLE_DATA_DIR = "usecli_data"


def _is_frozen() -> bool:
    """True when running from a PyInstaller bundle (onefile or onedir)."""
    return bool(getattr(sys, "frozen", False))


def _bundle_root() -> Path:
    """Top-level directory containing the frozen app + collected data."""
    if _is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(sys.argv[0]).resolve().parent if sys.argv else Path.cwd()


def _bundled_dir() -> Path:
    """The directory holding the bundled/dev project assets."""
    return _bundle_root() / BUNDLE_DATA_DIR


def _config_path() -> Path:
    """The project's ``usecli.config.toml`` for the current mode."""
    if _is_frozen():
        return _bundled_dir() / "usecli.config.toml"
    from usecli.bundler import _resolve_config_path

    return _resolve_config_path(None)


def _pyproject_path(config_path: Path) -> Path | None:
    """The project's ``pyproject.toml`` for the current mode, if any."""
    if _is_frozen():
        candidate = _bundled_dir() / "pyproject.toml"
        return candidate if candidate.exists() else None
    from usecli.bundler import _find_pyproject

    return _find_pyproject(config_path.parent)


def _inject_config() -> None:
    """Point usecli's global ``ConfigManager`` at the project's assets.

    Construction with explicit ``usecli_config_path`` bypasses the CWD-walking
    ``_find_usecli_config`` discovery (which filters by ``sys.argv[0]`` and
    would not match a project's nested config). Seeding the module-level
    ``_config_manager`` singleton is the supported override seam (``get_config``
    / ``reset_config`` exist for exactly this).
    """
    from usecli.shared.config import manager as mgr
    from usecli.shared.config.manager import ConfigManager

    config_path = _config_path()
    if not config_path.exists():
        raise FileNotFoundError(
            f"Could not locate usecli.config.toml. Expected at: {config_path}."
        )

    manager = ConfigManager(
        start_dir=config_path.parent,
        pyproject_path=_pyproject_path(config_path),
        usecli_config_path=config_path,
    )

    # Install as the global singleton get_config() returns. get_config() only
    # rebuilds when _config_cwd differs from the live cwd, so seed it with the
    # current cwd to guarantee our manager is returned.
    mgr._config_manager = manager
    mgr._config_cwd = Path.cwd().resolve()


def _command_name() -> str:
    """Canonical CLI name from the injected config (e.g. ``magic``)."""
    from usecli.shared.config.manager import get_config

    return (get_config().get("command_name") or "usecli") or "usecli"


def _exec_target() -> str:
    """Shell-fragment that re-invokes THIS CLI with the given argv.

    * Frozen: ``sys.executable`` is the bundled binary itself.
    * Source: the current interpreter + the running ``main.py``.
    """
    if _is_frozen():
        return f'"{sys.executable}"'
    script = Path(sys.argv[0]).resolve() if sys.argv else Path("main.py").resolve()
    return f'"{sys.executable}" "{script}"'


def _ensure_command_on_path() -> None:
    """Make the CLI resolvable on PATH for usecli's interactive runner.

    usecli's interactive (fzf) runner does NOT call commands in-process — it
    re-invokes them through a shell: ``subprocess.run(f"{cmd} ...", shell=True)``
    (aka ``/bin/sh -c "magic magic hello"``). Under a PyInstaller bundle the
    binary is never installed on PATH, so those shell-outs would fail with
    "command not found". We inject a tiny, self-referential ``<command_name>``
    launcher (and, in source mode, a launcher for the running ``main.py``) into
    a temp dir that is prepended to PATH.
    """
    names = {_command_name()}
    if not _is_frozen() and sys.argv:
        names.add(Path(sys.argv[0]).name)
    names.discard("")
    if not names:
        return
    shim_dir = Path(tempfile.mkdtemp(prefix="usecli-path-"))
    for name in names:
        shim = shim_dir / name
        shim.write_text(f'#!/bin/sh\nexec {_exec_target()} "$@"\n', encoding="utf-8")
        shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    current = os.environ.get("PATH", "")
    os.environ["PATH"] = str(shim_dir) + (os.pathsep + current if current else "")


def main() -> None:
    """Run the usecli CLI with the project's (injected) configuration."""
    from usecli import main as _usecli_main

    _inject_config()
    _ensure_command_on_path()
    _usecli_main()


if __name__ == "__main__":
    main()
