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
    gh release create "v$VERSION" --generate-notes
else
    echo "Release cancelled."
fi
