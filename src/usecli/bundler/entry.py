"""Runtime entry point for usecli-built PyInstaller executables.

This module is the analysis target for the single-file bundles produced by
:func:`usecli.pyinstaller.pyinstaller`. At runtime it:

* Points usecli's global :class:`~usecli.shared.config.manager.ConfigManager` at
  the project assets (``usecli.config.toml``, ``commands/``, ``templates/``,
  ``themes/``, ``pyproject.toml``) that the PyInstaller spec drops under
  ``sys._MEIPASS/<BUNDLE_DATA_DIR>`` — without ever walking the filesystem for
  discovery (no CWD / ``rglob`` search under the frozen bundle).
* Keeps the CLI resolvable on PATH so usecli's interactive (fzf) runner's
  shell-outs (``/bin/sh -c "magic magic hello"``) succeed even though the
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


def _bundle_root() -> Path:
    """Top-level directory containing the frozen app + collected data."""
    return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))


def _data_root() -> Path:
    """Directory containing the bundled project assets."""
    return _bundle_root() / BUNDLE_DATA_DIR


def _inject_config() -> None:
    """Point usecli's global ``ConfigManager`` at the bundled paths.

    Construction with explicit ``usecli_config_path`` bypasses the CWD-walking
    ``_find_usecli_config`` discovery. Seeding the module-level
    ``_config_manager`` singleton is the supported override seam (``get_config``
    / ``reset_config`` exist for exactly this).
    """
    from usecli.shared.config import manager as mgr
    from usecli.shared.config.manager import ConfigManager

    data = _data_root()
    config_path = data / "usecli.config.toml"
    pyproject_path = data / "pyproject.toml"

    if not config_path.exists():
        raise FileNotFoundError(
            "Could not locate the bundled usecli.config.toml. "
            f"Expected at: {config_path}. Rebuild the binary with "
            "usecli.pyinstaller()."
        )

    manager = ConfigManager(
        start_dir=data,
        pyproject_path=pyproject_path if pyproject_path.exists() else None,
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
    """Shell-fragment that re-invokes THIS (frozen) CLI with the given argv."""
    return f'"{sys.executable}"'


def _ensure_command_on_path() -> None:
    """Make the frozen CLI resolvable on PATH for usecli's interactive runner.

    usecli's interactive (fzf) runner does NOT call commands in-process — it
    re-invokes them through a shell: ``subprocess.run(f"{cmd} ...", shell=True)``
    (aka ``/bin/sh -c "magic magic hello"``). Under a PyInstaller bundle the
    binary is never installed on PATH, so those shell-outs would fail with
    "command not found". We inject a tiny, self-referential ``<command_name>``
    launcher into a temp dir that is prepended to PATH.
    """
    name = _command_name()
    if not name:
        return
    shim_dir = Path(tempfile.mkdtemp(prefix=f"{name}-path-"))
    shim = shim_dir / name
    shim.write_text(f'#!/bin/sh\nexec {_exec_target()} "$@"\n', encoding="utf-8")
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    current = os.environ.get("PATH", "")
    os.environ["PATH"] = str(shim_dir) + (os.pathsep + current if current else "")


def main() -> None:
    """Run the usecli CLI with bundled (injected) configuration."""
    from usecli import main as _usecli_main

    _inject_config()
    _ensure_command_on_path()
    _usecli_main()


if __name__ == "__main__":
    main()
