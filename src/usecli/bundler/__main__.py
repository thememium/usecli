"""Allow ``python -m usecli.bundler`` to build a single-file executable."""

from usecli.bundler import cli

if __name__ == "__main__":
    raise SystemExit(cli())
