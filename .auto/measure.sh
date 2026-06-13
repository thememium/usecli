#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_ROOT="${TMPDIR:-/tmp}/usecli-autoresearch-bench"
rm -rf "$TMP_ROOT"
mkdir -p "$TMP_ROOT"
export USECLI_BENCH_ROOT="$TMP_ROOT"
export USECLI_REPO_ROOT="$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
uv run python - <<'PY'
from __future__ import annotations

import os
import shutil
import statistics
import subprocess
import sys
import textwrap
import time
from pathlib import Path

root = Path(os.environ["USECLI_REPO_ROOT"])
tmp = Path(os.environ["USECLI_BENCH_ROOT"])
python = sys.executable

def write(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s)

# Downstream app with many commands and many unrelated files/configs that must not be selected.
dep = tmp / "dep_app"
write(dep / "pyproject.toml", '[project]\nname = "dep-app"\nversion = "1.2.3"\ndependencies = ["usecli"]\n')
write(dep / "usecli.config.toml", '[usecli]\ncommand_name = "depcli"\ntitle = "Dep CLI"\ndescription = "Dependency CLI"\ncommands_dir = "commands"\n')
for i in range(60):
    write(dep / "commands" / f"cmd_{i}.py", f'''
from usecli import BaseCommand
class Cmd{i}Command(BaseCommand):
    def signature(self): return "cmd{i}"
    def description(self): return "Command {i}"
    def handle(self): pass
''')
# Noise that simulates a large tool/cache tree. Correct code should not scan all of this for each startup.
noise = tmp / "noise"
for i in range(120):
    write(noise / f"pkg_{i}" / "nested" / "usecli.config.toml", '[usecli]\ncommand_name = "other"\ntitle = "Wrong"\n')
    write(noise / f"pkg_{i}" / "commands" / "x.py", 'x = 1\n')
venv_noise = dep / ".venv" / "lib" / "python3.12" / "site-packages"
for i in range(80):
    write(venv_noise / f"junk_{i}" / "usecli.config.toml", '[usecli]\ncommand_name = "junk"\n')

# Self project-ish run from repo root uses package config and built-in commands.
self_code = r'''
import sys
sys.argv = ["usecli", "--version"]
from usecli.shared.config.manager import reset_config
reset_config()
import usecli
# Access enough to ensure config + command discovery already happened at import.
print(usecli.service.version)
'''

dep_code = r'''
import sys
sys.argv = ["depcli", "--version"]
from usecli.shared.config.manager import reset_config
reset_config()
import usecli
names = []
for info in usecli.app.registered_commands:
    if info.name:
        names.append(info.name)
if "cmd59" not in names:
    raise SystemExit(f"missing loaded command; got {len(names)}")
print(len(names))
'''

config_code = r'''
import sys
from pathlib import Path
sys.argv = ["depcli", "x"]
from usecli.shared.config.manager import ConfigManager
m = ConfigManager(start_dir=Path.cwd())
if m.get("command_name") != "depcli":
    raise SystemExit(m.get_all())
if m.get_project_commands_dir().name != "commands":
    raise SystemExit(m.get_project_commands_dir())
print(m.get("title"))
'''

def run_one(code: str, cwd: Path) -> float:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    t0 = time.perf_counter()
    subprocess.run([python, "-c", code], cwd=str(cwd), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, text=True)
    return (time.perf_counter() - t0) * 1000

def median_ms(code: str, cwd: Path, n: int = 7) -> float:
    vals = [run_one(code, cwd) for _ in range(n)]
    return statistics.median(vals)

# Warm caches without measuring first-run bytecode/import noise.
run_one(self_code, root)
run_one(dep_code, dep)
run_one(config_code, dep)

self_ms = median_ms(self_code, root)
dependency_ms = median_ms(dep_code, dep)
config_ms = median_ms(config_code, dep)
startup_ms = statistics.median([self_ms, dependency_ms, config_ms])
print(f"METRIC startup_ms={startup_ms:.3f}")
print(f"METRIC self_ms={self_ms:.3f}")
print(f"METRIC dependency_ms={dependency_ms:.3f}")
print(f"METRIC config_ms={config_ms:.3f}")
PY
