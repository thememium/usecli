#!/usr/bin/env bash
set -e

read -p "Continue with release? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    npx changelogen@latest --bump
    VERSION=$(node -p "require('./package.json').version")
    uv version "$VERSION"
    git add CHANGELOG.md package.json pyproject.toml
    git commit -m "chore(uv): update version"
    git tag "v$VERSION"
    git push --follow-tags
    NOTES_FILE=$(mktemp)
    VERSION="$VERSION" uv run python - <<'PY' > "$NOTES_FILE"
import os
from pathlib import Path

version = os.environ["VERSION"]
heading = f"## v{version}"
lines = Path("CHANGELOG.md").read_text().splitlines()

start = None
for idx, line in enumerate(lines):
    if line.strip() == heading:
        start = idx
        break

if start is None:
    raise SystemExit(f"Missing changelog entry for {heading}")

end = None
for idx in range(start + 1, len(lines)):
    if lines[idx].startswith("## "):
        end = idx
        break

section = lines[start:end]
print("\n".join(section).rstrip())
PY
    gh release create "v$VERSION" --notes-file "$NOTES_FILE"
else
    echo "Release cancelled."
fi
