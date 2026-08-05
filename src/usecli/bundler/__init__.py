"""PyInstaller integration for usecli projects.

Every usecli project is a thin layer over usecli: it provides a
``usecli.config.toml`` plus ``commands/``, ``templates/`` and ``themes/`` that
usecli loads at runtime. Packaging that with PyInstaller by hand requires a
hand-written spec, ``--collect-all`` flags and a custom entry point that
re-injects the bundle paths — easy to get wrong.

:func:`pyinstaller` turns all of that into a one-liner::

    from usecli import pyinstaller
    pyinstaller()              # auto-detect config from the current directory
    pyinstaller("config.toml") # or point at a specific config

It locates the project's ``usecli.config.toml`` (and the sibling
``commands/``, ``templates/``, ``themes/`` and ``pyproject.toml``), then runs
PyInstaller to produce a single-file executable named after the config's
``command_name``. PyInstaller is an optional dependency — install it with
``pip install usecli[pyinstaller]`` (or ``uv add usecli[pyinstaller]``).
"""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from pathlib import Path

from usecli.entry import BUNDLE_DATA_DIR


def _resolve_config_path(
    config_path: str | os.PathLike[str] | None,
) -> Path:
    """Return an absolute, existing path to the project's usecli.config.toml.

    When ``config_path`` is ``None``, it is auto-detected: first by walking up
    from the current directory, then (e.g. configs nested under ``cli/``) via a
    bounded recursive search rooted at the detected project root.
    """
    if config_path is not None:
        resolved = Path(config_path).resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"usecli.config.toml not found at: {resolved}")
        return resolved

    from usecli.shared.config.manager import resolve_config_path

    return resolve_config_path(Path.cwd())


def _find_pyproject(data_root: Path) -> Path | None:
    """Find the nearest pyproject.toml walking up from the data dir."""
    from usecli.shared.config.manager import find_project_pyproject

    return find_project_pyproject(data_root)


def _build_args(
    config_path: Path,
    entry_path: Path,
    *,
    name: str | None,
    distpath: Path | None,
    workpath: Path | None,
    extra_args: Sequence[str] | None,
) -> list[str]:
    from usecli.shared.config.manager import ConfigManager

    data_root = config_path.parent
    command_name = name or (
        ConfigManager._load_usecli_toml(config_path).get("command_name") or "usecli"
    )
    pyproject = _find_pyproject(data_root)

    args: list[str] = ["--onefile", "--name", command_name]
    if distpath is not None:
        args += ["--distpath", str(distpath)]
    if workpath is not None:
        args += ["--workpath", str(workpath)]
    args += [
        "--collect-all",
        "usecli",
        "--collect-all",
        "pyfiglet",
        "--add-data",
        f"{data_root}{os.pathsep}{BUNDLE_DATA_DIR}",
        "--paths",
        str(data_root.parent),
        "-y",
    ]
    if pyproject is not None:
        args += ["--add-data", f"{pyproject}{os.pathsep}{BUNDLE_DATA_DIR}"]
    if extra_args:
        args += list(extra_args)
    args.append(str(entry_path))
    return args


def pyinstaller(
    config_path: str | os.PathLike[str] | None = None,
    *,
    name: str | None = None,
    distpath: str | os.PathLike[str] | None = None,
    workpath: str | os.PathLike[str] | None = None,
    extra_args: Sequence[str] | None = None,
) -> int:
    """Build a single-file executable for the given usecli project.

    Args:
        config_path: Optional path to a ``usecli.config.toml``. When omitted it
            is auto-detected by walking up from the current directory.
        name: Optional override for the executable name. Defaults to the
            config's ``command_name``.
        distpath: Output directory for the executable (default: ``./dist``).
        workpath: PyInstaller work directory (default: ``./build``).
        extra_args: Additional PyInstaller CLI flags, e.g.
            ``["--icon", "icon.icns"]``.

    Returns:
        The PyInstaller exit code (``0`` on success).

    Raises:
        FileNotFoundError: if no config can be located / the given path is not
            a file.
        ImportError: if PyInstaller is not installed. Install with
            ``pip install usecli[pyinstaller]``.
    """
    resolved = _resolve_config_path(config_path)
    import usecli.entry as entry_module

    entry_path = Path(entry_module.__file__)

    try:
        from PyInstaller.__main__ import run as _pyinstaller_run
    except ImportError as exc:  # pragma: no cover - env dependent
        raise ImportError(
            "PyInstaller is required to build an executable. Install it with "
            "`pip install usecli[pyinstaller]` (or `uv add usecli[pyinstaller]`)."
        ) from exc

    args = _build_args(
        resolved,
        entry_path,
        name=name,
        distpath=Path(distpath) if distpath is not None else None,
        workpath=Path(workpath) if workpath is not None else None,
        extra_args=extra_args,
    )

    print(
        f"[usecli] Packaging '{args[args.index('--name') + 1]}' "
        f"from {resolved} as a single-file executable..."
    )
    code = _pyinstaller_run(args)
    if isinstance(code, int) and code != 0:
        raise SystemExit(code)
    return int(code or 0)


def cli(argv: Sequence[str] | None = None) -> int:
    """Command-line interface backing the ``usecli-bundle`` console script.

    So a project's pyproject.toml never needs to carry PyInstaller flags —
    ``uv run usecli-bundle`` auto-detects the config and builds the onefile::

        [tool.poe.tasks]
        bundle = "uv run usecli-bundle"
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="usecli-bundle",
        description="Build a single-file executable for the current usecli project.",
    )
    parser.add_argument(
        "config_path",
        nargs="?",
        default=None,
        help="Path to usecli.config.toml (auto-detected when omitted).",
    )
    parser.add_argument("--name", default=None, help="Executable name override.")
    parser.add_argument("--distpath", default=None, help="Output directory.")
    parser.add_argument("--workpath", default=None, help="PyInstaller work dir.")
    known, extra = parser.parse_known_args(argv)
    return pyinstaller(
        config_path=known.config_path,
        name=known.name,
        distpath=known.distpath,
        workpath=known.workpath,
        extra_args=extra or None,
    )


if __name__ == "__main__":  # pragma: no cover - convenience CLI
    sys.exit(cli())
