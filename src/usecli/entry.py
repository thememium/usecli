"""Public runtime entry point for usecli projects.

A project can run its CLI through here directly — no PyInstaller needed — from a
thin ``main.py``::

    from usecli import run

    def main():
        run()                         # auto-detect the project config
        # run("my/custom/cli.toml")   # or point at a specific config

    if __name__ == "__main__":
        main()

It works in three contexts:

* **Development** (``uv run main.py``): locates the project's
  ``usecli.config.toml`` from the current directory via the default finder
  (:func:`usecli.shared.config.manager.resolve_config_path`) and injects it
  explicitly — no ``get_config()`` discovery (which is filtered by the runtime
  command name / ``sys.argv[0]``) is involved.
* **Frozen** (PyInstaller one-file): reads the assets bundled under
  ``sys._MEIPASS/<BUNDLE_DATA_DIR>`` with no filesystem discovery.
* **Explicit**: passing a config path lets callers build their own entry points
  instead of relying on the default finder.

In dev/frozen modes it also keeps the CLI resolvable on PATH so the interactive
(fzf) runner's shell-outs succeed even though the binary is never installed on
PATH.
"""

from __future__ import annotations

import os
import stat
import sys
import tempfile
from pathlib import Path

# Subdirectory (under sys._MEIPASS) where the spec drops the project assets.
# The bundle builder imports this constant so the runtime and build agree.
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
    """The directory holding the bundled project assets."""
    return _bundle_root() / BUNDLE_DATA_DIR


def _resolve_config(config_path: str | os.PathLike[str] | None = None) -> Path:
    """The project's ``usecli.config.toml`` for the current context.

    Explicit ``config_path`` wins; otherwise the frozen bundle is used when
    frozen, else the default finder from the current directory.
    """
    if config_path is not None:
        resolved = Path(config_path).resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"usecli.config.toml not found at: {resolved}")
        return resolved
    if _is_frozen():
        return _bundled_dir() / "usecli.config.toml"
    from usecli.shared.config.manager import resolve_config_path

    return resolve_config_path(Path.cwd())


def _resolve_pyproject(
    config_path: Path, pyproject_path: str | os.PathLike[str] | None
) -> Path | None:
    """The project's ``pyproject.toml`` for the current context, if any."""
    if pyproject_path is not None:
        resolved = Path(pyproject_path)
        return resolved if resolved.exists() else None
    if _is_frozen():
        candidate = _bundled_dir() / "pyproject.toml"
        return candidate if candidate.exists() else None
    from usecli.shared.config.manager import find_project_pyproject

    return find_project_pyproject(config_path.parent)


def _inject_config(
    config_path: str | os.PathLike[str] | None = None,
    pyproject_path: str | os.PathLike[str] | None = None,
) -> None:
    """Point usecli's global ``ConfigManager`` at the project's assets.

    Construction with explicit ``usecli_config_path`` bypasses the CWD-walking
    ``_find_usecli_config`` discovery (which filters by ``sys.argv[0]`` and
    would not match a project's config). Seeding the module-level
    ``_config_manager`` singleton is the supported override seam (``get_config``
    / ``reset_config`` exist for exactly this).
    """
    from usecli.shared.config import manager as mgr
    from usecli.shared.config.manager import ConfigManager

    resolved = _resolve_config(config_path)
    if not resolved.exists():
        raise FileNotFoundError(
            f"Could not locate usecli.config.toml. Expected at: {resolved}."
        )

    manager = ConfigManager(
        start_dir=resolved.parent,
        pyproject_path=_resolve_pyproject(resolved, pyproject_path),
        usecli_config_path=resolved,
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


def run(
    config_path: str | os.PathLike[str] | None = None,
    *,
    pyproject_path: str | os.PathLike[str] | None = None,
    on_path: bool = True,
) -> None:
    """Run the usecli CLI for a project.

    Args:
        config_path: Optional ``usecli.config.toml`` path. When omitted it is
            auto-detected: from the frozen bundle when running under PyInstaller,
            otherwise via the default finder from the current directory.
        pyproject_path: Optional ``pyproject.toml`` path (used for version info).
        on_path: Whether to expose the CLI on ``PATH`` so the interactive
            runner's shell-outs resolve it.
    """
    _inject_config(config_path=config_path, pyproject_path=pyproject_path)
    if on_path:
        _ensure_command_on_path()
    from usecli import main as _usecli_main

    _usecli_main()


def main() -> None:
    """Convenience alias for :func:`run` with default arguments."""
    run()


if __name__ == "__main__":
    main()
