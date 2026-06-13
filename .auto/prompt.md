# Autoresearch: usecli startup/config/command discovery speed

## Objective
Make the `usecli` CLI extremely fast and efficient at startup, both when run as `usecli` itself and when used as a dependency by another app's CLI. The hot path must quickly find the correct installed package config and parse/load the intended `commands` folder only. In global `uv tool`-style installs, avoid accidentally walking broad filesystem roots or unrelated directories; search should be bounded to the current project/package/console-script install.

## Metrics
- **Primary**: `startup_ms` (ms, lower is better) — median wall-clock time for representative CLI startup/config/command discovery workloads.
- **Secondary**: `self_ms`, `dependency_ms`, `config_ms`, `tests_s` — monitor tradeoffs across scenarios.

## How to Run
`./.auto/measure.sh` — emits `METRIC name=value` lines.

## Files in Scope
- `src/usecli/__init__.py` — CLI construction/startup and global command service load.
- `src/usecli/cli/services/command_service.py` — command folder scanning/import/registration.
- `src/usecli/shared/config/manager.py` — config discovery, project root detection, package/console script resolution.
- `src/usecli/shared/config/globals.py` — package/config path constants.
- Tests under `tests/` that cover changed behavior.

## Off Limits
- Do not cheat by special-casing `.auto` benchmark paths, command names, or test fixtures.
- Do not remove required command discovery/config semantics.
- Do not add new runtime dependencies.
- Do not globally skip project commands or package configs; fixes must be generally correct.

## Constraints
- Preserve correctness for usecli direct use and downstream package CLIs.
- Avoid broad recursive filesystem scans, especially from `/`, home, virtualenv roots, or large project roots when a more precise package/console-script location exists.
- Keep benchmark honest: representative temporary projects, many command files, and unrelated configs should still resolve correctly.
- Existing tests should pass; `.auto/checks.sh` runs focused pytest.

## What's Been Tried
- Baseline setup in progress. Initial source reading found likely hotspots in `ConfigManager._find_usecli_config`, `_get_console_script_aliases`, `_find_usecli_config_for_console_script`, and recursive `rglob` usage in both config and command discovery.
