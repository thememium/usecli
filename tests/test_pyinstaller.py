"""Tests for usecli.pyinstaller — the PyInstaller one-liner integration."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from usecli import entry as entry_mod
from usecli import pyinstaller
from usecli.bundler import (
    BUNDLE_DATA_DIR,
    _build_args,
    _find_pyproject,
    _resolve_config_path,
    cli,
)


def _write_project(tmp_path: Path, *, command_name: str = "magic") -> Path:
    """Create a minimal usecli project tree and return the config path."""
    cli = tmp_path / "cli"
    (cli / "commands").mkdir(parents=True)
    (cli / "templates").mkdir()
    (cli / "themes").mkdir()
    config = cli / "usecli.config.toml"
    config.write_text(
        f"""[usecli]
command_name = "{command_name}"
title = "{command_name}"
commands_dir = "commands"
templates_dir = "templates"
themes_dir = "themes"
""",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "1.2.3"\n',
        encoding="utf-8",
    )
    return config


def test_exposed_lazily():
    """`pyinstaller` is importable from the top-level namespace."""
    assert callable(pyinstaller)


def test_resolve_config_path_explicit(tmp_path):
    config = _write_project(tmp_path)
    resolved = _resolve_config_path(str(config))
    assert resolved == config.resolve()


def test_resolve_config_path_missing_explicit(tmp_path):
    with pytest.raises(FileNotFoundError):
        _resolve_config_path(str(tmp_path / "nope" / "usecli.config.toml"))


def test_resolve_config_path_auto_up_walk(tmp_path, monkeypatch):
    (tmp_path / "usecli.config.toml").write_text(
        '[usecli]\ncommand_name = "rootcli"\n', encoding="utf-8"
    )
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    resolved = _resolve_config_path(None)
    assert resolved == (tmp_path / "usecli.config.toml").resolve()


def test_resolve_config_path_auto_nested_in_cli(tmp_path, monkeypatch):
    config = _write_project(tmp_path, command_name="nested")
    monkeypatch.chdir(tmp_path)
    resolved = _resolve_config_path(None)
    # Config nested under cli/ is found via the project-root tree search.
    assert resolved == config.resolve()


def test_resolve_config_path_none_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # empty dir, no config, no pyproject
    with pytest.raises(FileNotFoundError):
        _resolve_config_path(None)


def test_build_args_shape(tmp_path):
    config = _write_project(tmp_path)
    entry = tmp_path / "entry.py"
    args = _build_args(
        config,
        entry,
        name=None,
        distpath=tmp_path / "out",
        workpath=tmp_path / "work",
        extra_args=["--icon", "icon.icns"],
    )
    assert "--onefile" in args
    assert "--name" in args and args[args.index("--name") + 1] == "magic"
    assert ["--collect-all", "usecli"] == args[
        args.index("--collect-all") : args.index("--collect-all") + 2
    ]
    # pyfiglet is collected too.
    assert args.count("--collect-all") == 2
    # Config assets are added under BUNDLE_DATA_DIR.
    add_data = args[args.index("--add-data") + 1].rsplit(":", 1)
    assert add_data[0] == str(config.parent)
    assert add_data[1] == BUNDLE_DATA_DIR
    assert args[-1] == str(entry)
    assert "--distpath" in args and "--workpath" in args


def test_build_args_name_override(tmp_path):
    config = _write_project(tmp_path, command_name="magic")
    args = _build_args(
        config,
        tmp_path / "entry.py",
        name="renamed",
        distpath=None,
        workpath=None,
        extra_args=None,
    )
    assert args[args.index("--name") + 1] == "renamed"


def test_pyinstaller_runs_pyinstaller(tmp_path, monkeypatch):
    _write_project(tmp_path, command_name="magic")
    monkeypatch.chdir(tmp_path)
    captured: dict = {}

    def fake_run(pyi_args: list[str] | None = None, pyi_config: dict | None = None):
        captured["args"] = list(pyi_args or [])
        return 0

    with patch("PyInstaller.__main__.run", new=fake_run):
        code = pyinstaller()
    assert code == 0
    # Auto-detects the nested config and passes the embedded entry as target.
    assert "usecli_data" in captured["args"][captured["args"].index("--add-data") + 1]
    assert "--name" in captured["args"]
    assert captured["args"][-1].endswith("entry.py")


def test_cli_entry_point(tmp_path, monkeypatch):
    config = _write_project(tmp_path, command_name="magic")
    monkeypatch.chdir(tmp_path)
    captured: dict = {}

    def fake_run(pyi_args: list[str] | None = None, pyi_config: dict | None = None):
        captured["args"] = list(pyi_args or [])
        return 0

    with patch("PyInstaller.__main__.run", new=fake_run):
        code = cli(["--name", "renamed"])
    assert code == 0
    # Explicit name override is honored by the CLI arg parser.
    assert captured["args"][captured["args"].index("--name") + 1] == "renamed"
    assert (
        str(config.parent) in captured["args"][captured["args"].index("--add-data") + 1]
    )


def test_cli_entry_point_explicit_config(tmp_path, monkeypatch):
    config = _write_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    captured: dict = {}

    def fake_run(pyi_args: list[str] | None = None, pyi_config: dict | None = None):
        captured["args"] = list(pyi_args or [])
        return 0

    with patch("PyInstaller.__main__.run", new=fake_run):
        cli([str(config)])
    assert captured["args"][captured["args"].index("--add-data") + 1] == (
        config.parent.as_posix() + ":" + BUNDLE_DATA_DIR
    )


def test_pyinstaller_requires_pyinstaller(tmp_path, monkeypatch):
    _write_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        # Only block the PyInstaller import; config resolution still works.
        if name == "PyInstaller.__main__":
            raise ImportError("No module named 'PyInstaller.__main__'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    with pytest.raises(ImportError, match=r"usecli\[pyinstaller\]"):
        pyinstaller()


# =============================================================================
# Bundler internals: _find_pyproject / failure exit
# =============================================================================


def test_build_args_no_pyproject(tmp_path):
    # Config whose ancestor tree has no pyproject.toml -> only the data root is
    # bundled (no --add-data for a pyproject).
    data_dir = tmp_path / "cli"
    data_dir.mkdir()
    config = data_dir / "usecli.config.toml"
    config.write_text('[usecli]\ncommand_name = "x"\n', encoding="utf-8")
    args = _build_args(
        config,
        tmp_path / "entry.py",
        name=None,
        distpath=None,
        workpath=None,
        extra_args=None,
    )
    assert args.count("--add-data") == 1
    assert args[args.index("--add-data") + 1].endswith(":" + BUNDLE_DATA_DIR)


def test_find_pyproject_walks_up(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    data_root = project / "cli" / "nested"
    data_root.mkdir(parents=True)
    # Returns the nearest pyproject even when starting deep inside.
    assert _find_pyproject(data_root) == (project / "pyproject.toml").resolve()


def test_pyinstaller_failure_raises_systemexit(monkeypatch, tmp_path):
    _write_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    with (
        patch("PyInstaller.__main__.run", return_value=1),
        pytest.raises(SystemExit) as exc,
    ):
        pyinstaller()
    assert exc.value.code == 1


# =============================================================================
# Runtime entry module (frozen-bundle behavior)
# =============================================================================


def _prepare_dev_project(tmp_path):
    """Place a project with a nested cli/ config, chdir into it."""
    config = _write_project(tmp_path, command_name="magic")
    return config


def _freeze(monkeypatch, bundle: Path | None):
    """Simulate a PyInstaller frozen env, optionally at a bundle dir."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    if bundle is None:
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    else:
        monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)


def _make_frozen_bundle(tmp_path) -> Path:
    """Build a fake ``sys._MEIPASS`` tree with one bundled config."""
    bundle = tmp_path / "_MEIPASS"
    data = bundle / BUNDLE_DATA_DIR
    data.mkdir(parents=True)
    (data / "usecli.config.toml").write_text(
        '[usecli]\ncommand_name = "bundled"\n', encoding="utf-8"
    )
    (data / "pyproject.toml").write_text(
        '[project]\nname = "x"\nversion = "9.9.9"\n', encoding="utf-8"
    )
    return bundle


# ---------------------------------------------------------------------------
# Mode detection
# ---------------------------------------------------------------------------


def test_is_frozen_true(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert entry_mod._is_frozen() is True


def test_is_frozen_false():
    assert entry_mod._is_frozen() is False


# ---------------------------------------------------------------------------
# Frozen mode
# ---------------------------------------------------------------------------


def test_bundle_root_uses_meipass(monkeypatch):
    _freeze(monkeypatch, Path("/bundled/x"))
    assert entry_mod._bundle_root() == Path("/bundled/x")


def test_bundle_root_fallback(monkeypatch):
    _freeze(monkeypatch, None)
    assert entry_mod._bundle_root() == Path(sys.executable).parent


def test_bundled_dir(monkeypatch):
    _freeze(monkeypatch, Path("/bundled/x"))
    assert entry_mod._bundled_dir() == Path("/bundled/x") / BUNDLE_DATA_DIR


def test_resolve_config_frozen(monkeypatch, tmp_path):
    bundle = _make_frozen_bundle(tmp_path)
    _freeze(monkeypatch, bundle)
    assert (
        entry_mod._resolve_config() == bundle / BUNDLE_DATA_DIR / "usecli.config.toml"
    )


def test_inject_config_frozen(monkeypatch, tmp_path):
    from usecli.shared.config import manager as mgr

    bundle = _make_frozen_bundle(tmp_path)
    _freeze(monkeypatch, bundle)
    try:
        entry_mod._inject_config()
        assert mgr._config_manager is not None
        assert (
            mgr._config_manager.usecli_config_path.resolve()
            == (bundle / BUNDLE_DATA_DIR / "usecli.config.toml").resolve()
        )
    finally:
        mgr.reset_config()


def test_inject_config_missing(monkeypatch, tmp_path):
    bundle = tmp_path / "_MEIPASS"
    (bundle / BUNDLE_DATA_DIR).mkdir(parents=True)  # no config file inside
    _freeze(monkeypatch, bundle)
    with pytest.raises(FileNotFoundError):
        entry_mod._inject_config()


def test_exec_target_frozen(monkeypatch):
    _freeze(monkeypatch, None)
    monkeypatch.setattr(sys, "executable", "/usr/bin/python")
    assert entry_mod._exec_target() == '"/usr/bin/python"'


def test_ensure_command_on_path_frozen(monkeypatch):
    _freeze(monkeypatch, None)
    monkeypatch.setattr(entry_mod, "_command_name", lambda: "magic")
    monkeypatch.setattr(sys, "argv", ["whatever"])
    old_path = os.environ.get("PATH", "")
    try:
        entry_mod._ensure_command_on_path()
        shim_dir = os.environ["PATH"].split(os.pathsep)[0]
        shim = Path(shim_dir) / "magic"
        assert shim.is_file()
        assert os.access(shim, os.X_OK)
        # Frozen mode does NOT add an argv[0] shim.
        assert not (Path(shim_dir) / "whatever").exists()
    finally:
        os.environ["PATH"] = old_path


# ---------------------------------------------------------------------------
# Development mode (uv run main.py, no PyInstaller)
# ---------------------------------------------------------------------------


def test_bundle_root_dev(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["/proj/main.py"])
    assert entry_mod._bundle_root() == Path("/proj/main.py").resolve().parent


def test_resolve_config_dev(monkeypatch, tmp_path):
    config = _prepare_dev_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py"])
    assert entry_mod._resolve_config().resolve() == config.resolve()


def test_inject_config_dev(monkeypatch, tmp_path):
    from usecli.shared.config import manager as mgr

    config = _prepare_dev_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py"])
    try:
        entry_mod._inject_config()
        assert mgr._config_manager is not None
        assert mgr._config_manager.usecli_config_path.resolve() == config.resolve()
    finally:
        mgr.reset_config()


def test_exec_target_dev(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["/abs/main.py"])
    monkeypatch.setattr(sys, "executable", "/usr/bin/python")
    assert entry_mod._exec_target() == '"/usr/bin/python" "/abs/main.py"'


def test_ensure_command_on_path_dev(monkeypatch):
    monkeypatch.setattr(entry_mod, "_command_name", lambda: "magic")
    monkeypatch.setattr(sys, "argv", ["main.py"])
    old_path = os.environ.get("PATH", "")
    try:
        entry_mod._ensure_command_on_path()
        shim_dir = os.environ["PATH"].split(os.pathsep)[0]
        # Both the command name and the running main.py are shimmed.
        assert (Path(shim_dir) / "magic").is_file()
        assert (Path(shim_dir) / "main.py").is_file()
    finally:
        os.environ["PATH"] = old_path


def test_ensure_command_on_path_no_name(monkeypatch):
    monkeypatch.setattr(entry_mod, "_command_name", lambda: "")
    monkeypatch.setattr(sys, "argv", [])
    old_path = os.environ.get("PATH", "")
    try:
        entry_mod._ensure_command_on_path()
        assert os.environ.get("PATH", "") == old_path
    finally:
        os.environ["PATH"] = old_path


def test_entry_main_calls_inject_path_and_cli(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        entry_mod, "_inject_config", lambda *a, **k: calls.append("inject")
    )
    monkeypatch.setattr(
        entry_mod, "_ensure_command_on_path", lambda *a, **k: calls.append("path")
    )
    monkeypatch.setattr("usecli.main", lambda: calls.append("usecli_main"))
    entry_mod.main()
    assert calls == ["inject", "path", "usecli_main"]


def test_entry_main_guard(monkeypatch, tmp_path):
    import runpy

    from usecli.shared.config import manager as mgr

    bundle = _make_frozen_bundle(tmp_path)
    _freeze(monkeypatch, bundle)
    monkeypatch.setattr("usecli.main", lambda: None)
    old_path = os.environ.get("PATH", "")
    try:
        runpy.run_path(str(Path(entry_mod.__file__)), run_name="__main__")
    finally:
        mgr.reset_config()
        os.environ["PATH"] = old_path


def test_main_module_entry(monkeypatch, tmp_path):
    import runpy

    _write_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["usecli.bundler"])
    with (
        patch("PyInstaller.__main__.run", return_value=0),
        pytest.raises(SystemExit) as exc,
    ):
        runpy.run_module("usecli.bundler", run_name="__main__")
    assert exc.value.code == 0


# =============================================================================
# Public run() entry-point API (bundler-free main.py)
# =============================================================================


def test_run_exposed_lazily():
    from usecli import run

    assert callable(run)


def test_run_explicit_config_path(monkeypatch, tmp_path):
    from usecli.shared.config import manager as mgr

    config = _write_project(tmp_path, command_name="custom")
    calls: list[str] = []
    monkeypatch.setattr("usecli.main", lambda: calls.append("cli"))
    try:
        entry_mod.run(str(config), on_path=False)
        assert mgr._config_manager is not None
        assert mgr._config_manager.usecli_config_path.resolve() == config.resolve()
        assert calls == ["cli"]
    finally:
        mgr.reset_config()


def test_run_explicit_pyproject_path(monkeypatch, tmp_path):
    from usecli.shared.config import manager as mgr

    config = _write_project(tmp_path)
    pyproject = tmp_path / "pyproject.toml"
    monkeypatch.setattr("usecli.main", lambda: None)
    try:
        entry_mod.run(str(config), pyproject_path=str(pyproject), on_path=False)
        assert mgr._config_manager is not None
        assert mgr._config_manager.pyproject_path.resolve() == pyproject.resolve()
    finally:
        mgr.reset_config()


def test_run_auto_detect_dev(monkeypatch, tmp_path):
    from usecli.shared.config import manager as mgr

    config = _prepare_dev_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py"])
    calls: list[str] = []
    monkeypatch.setattr("usecli.main", lambda: calls.append("cli"))
    try:
        entry_mod.run(on_path=False)
        assert mgr._config_manager is not None
        assert mgr._config_manager.usecli_config_path.resolve() == config.resolve()
        assert calls == ["cli"]
    finally:
        mgr.reset_config()


def test_run_auto_detect_frozen(monkeypatch, tmp_path):
    from usecli.shared.config import manager as mgr

    bundle = _make_frozen_bundle(tmp_path)
    _freeze(monkeypatch, bundle)
    calls: list[str] = []
    monkeypatch.setattr("usecli.main", lambda: calls.append("cli"))
    try:
        entry_mod.run(on_path=False)
        assert mgr._config_manager is not None
        assert (
            mgr._config_manager.usecli_config_path.resolve()
            == (bundle / BUNDLE_DATA_DIR / "usecli.config.toml").resolve()
        )
        assert calls == ["cli"]
    finally:
        mgr.reset_config()


def test_run_missing_explicit_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        entry_mod.run(str(tmp_path / "nope" / "usecli.config.toml"))


def test_run_no_config_anywhere(monkeypatch, tmp_path):
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    with pytest.raises(FileNotFoundError):
        entry_mod.run(on_path=False)


def test_entry_main_delegates_to_run(monkeypatch):
    captured: dict = {}

    def fake_run(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(entry_mod, "run", fake_run)
    entry_mod.main()
    assert captured == {}
