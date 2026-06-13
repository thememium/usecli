#!/usr/bin/env bash
set -euo pipefail
uv run pytest tests/shared/config/test_manager.py tests/cli/services/test_command_service.py -q
