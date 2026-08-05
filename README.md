<a name="readme-top"></a>

<div align="center">
  <a href="https://github.com/thememium/usecli">
    <img src="https://raw.githubusercontent.com/thememium/usecli/refs/heads/master/docs/images/usecli-logo-dark-bg.png" alt="useCli" width="360" height="162">
  </a>

  <p align="center">
    <a href="#table-of-contents"><strong>Explore the Documentation »</strong></a>
    <br />
    <a href="https://github.com/thememium/usecli/issues">Report Bug</a>
    ·
    <a href="https://github.com/thememium/usecli/issues">Request Feature</a>
  </p>
</div>

<!-- TABLE OF CONTENTS -->

<a name="table-of-contents"></a>

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about">About</a></li>
    <li><a href="#quick-start">Quick Start</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#entry-points--packaging">Entry Points &amp; Packaging</a></li>
    <li><a href="#development">Development</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
  </ol>
</details>

<!-- ABOUT -->

## About

useCli A powerful Python CLI framework for building beautiful, developer-friendly command-line tools. It gives you:

- **Prefix matching** — Type `he` instead of `help`
- **Interactive mode** — Fuzzy finder for commands
- **Auto-generated help** — Clean, styled output
- **Command scaffolding** — `make:command` generates boilerplate
- **UI components** — Prompts, menus, styled console output

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- QUICK START -->

## Quick Start

### Install usecli with uv (recommended)

```sh
uv add usecli
```

### Install with pip (alternative)

```sh
pip install usecli
```

### Initialize

```sh
usecli init
```

### Create a command

```sh
usecli make:command hello
```

Your new command is ready in the commands directory:

```python
class HelloCommand(BaseCommand):
    def signature(self) -> str:
        return "hello"

    def description(self) -> str:
        return "Say hello"

    def handle(self, name: str = Argument(..., help="Your name")) -> None:
        console.print(f"Hello, {name}!")
```

Run it:

```sh
usecli hello world
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE -->

## Usage

### Prefix Matching

Type partial command names:

```sh
usecli he          # help
usecli ma:co       # make:command
```

### Interactive Mode

```sh
usecli --interactive    # Fuzzy finder for all commands
usecli -i hello         # Run 'hello' command interactively
```

### Command Groups

Colon-separated commands group automatically in help:

```python
def signature(self) -> str:
    return "db:migrate"
```

Displays as:

```
db:
  migrate    Run migrations
  backup     Backup database
```

Space-separated signatures create nested subcommands:

```python
def signature(self) -> str:
    return "spec show"  # usecli spec show
```

### JSON Output

Every command inherits `--json`; commands do not declare the option themselves. The flag works before or after a command name:

```sh
usecli --json about
usecli about --json
```

A successful invocation writes exactly one JSON document to stdout:

```json
{"ok":true,"data":null}
```

A command can return any JSON-serializable value to populate `data`:

```python
class StatusCommand(BaseCommand):
    def signature(self) -> str:
        return "status"

    def description(self) -> str:
        return "Show service status"

    def handle(self):
        return {"status": "ready", "workers": 3}
```

Failures preserve a non-zero exit status and use a stable error envelope:

```json
{"ok":false,"error":{"type":"UsageError","message":"No such command","code":2}}
```

In JSON mode, stdout is reserved for that document. Human-facing output, including `console.print()` and ordinary `print()`, is routed to stderr. Prompts and confirmations resolve their declared defaults without reading stdin. A prompt without a default, menus, and `--interactive` fail immediately with a structured `NonInteractiveError` instead of blocking.

The existing fields `ok`, `data`, `error`, `error.type`, `error.message`, and `error.code` keep their names and types across compatible releases. New fields may be added.

### UI Components

```python
from usecli import Confirm, Menu, Prompt, console

console.print("[green]Done![/green]")
name = Prompt.ask("Enter name")
ok = Confirm.ask("Continue?")
choice = Menu.select(["A", "B", "C"])
```

### Progress Indicators

Use `Spinner` when the amount of work is unknown and `ProgressBar` when a total is known:

```python
from usecli import ProgressBar, Spinner

with Spinner("Loading records") as spinner:
    load_records()
    spinner.update("Indexing records")

with ProgressBar(total=len(items), description="Processing") as progress:
    for item in items:
        process(item)
        progress.advance()
```

Progress always renders to stderr, uses the active usecli theme, and is suppressed automatically in JSON mode, with `quiet=True`, or when stderr is not attached to a terminal. Calling commands do not need to detect these conditions.

### Available Commands

```
about        Show app info
help         Show help
init         Initialize usecli (usecli only)
inspire      Random quote
make:command Create new command (usecli only)
make:theme   Create new theme (usecli only)
make:bundle  Build a standalone executable with PyInstaller (usecli only)
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ENTRY POINTS & PACKAGING -->

## Entry Points &amp; Packaging

A usecli CLI can be exposed in several ways, depending on how you distribute and
run it. There are three common setups — none requires anything but the base
`usecli` install, and the optional bundler adds PyInstaller packaging on top.

### 1. Default — console script (no entry point)

The simplest setup. Declare a console script in your project's `pyproject.toml`:

```toml
[project.scripts]
mycli = "usecli:main"
```

usecli resolves your project's config automatically from the current directory
(config discovery), so no `main.py` is required. Install and run it:

```sh
uv add usecli
uv run mycli --help
```

This is the **default** — no entry point file of your own is needed.

### 2. Custom entry point — `main.py`

If you want your own entry point, use the public runtime API. It works in both
development and frozen bundles, and accepts an optional config path (the config
file is always named `usecli.config.toml`):

```python
# main.py
from usecli import run

if __name__ == "__main__":
    run()  # auto-detect project config
    # run("path/to/usecli.config.toml")          # or point at a specific config
```

Run it in development (no PyInstaller required):

```sh
uv run python main.py --help
```

Because `run()` injects the located config explicitly, a custom `main.py` works
regardless of whether your CLI also has a `[project.scripts]` entry.

### 3. Bundler — standalone executable (optional, requires PyInstaller)

The bundler is an **optional** feature gated on PyInstaller being installed.
Install it with:

```sh
uv add "usecli[pyinstaller]"
```

Once installed, a `make:bundle` command appears (usecli only) that builds your
project into a standalone executable. It asks which mode to use via an
interactive menu, and confirms before building (defaults to no unless `-y`):

```sh
uv run usecli make:bundle                  # menu: one file vs one folder + confirm
uv run usecli make:bundle --mode onefile   # single-file executable
uv run usecli make:bundle --mode onedir    # one-folder bundle
uv run usecli make:bundle -y               # skip the confirmation
uv run usecli make:bundle --mode onedir -y # fully programmatic
uv run usecli make:bundle --mode onedir --zip -y  # one-folder bundle + zip
```

When building a **one-folder** bundle, `make:bundle` asks whether to also zip
the folder into `dist/<name>.zip` (PyInstaller's recommended distribution
format for one-folder mode). Pass `--zip` / `--no-zip` to skip the prompt and
force a choice; with `-y` and no flag, zipping is skipped.

A `usecli-bundle` console script wraps the same build, and you can drive it from
Python too:

```sh
uv run usecli-bundle
uv run usecli-bundle --mode onedir
uv run usecli-bundle --mode onedir --zip
```

```python
from usecli import pyinstaller

pyinstaller()  # auto-detect config, single-file
pyinstaller(mode="onedir")  # one-folder bundle
pyinstaller(mode="onedir", zip=True)  # one-folder bundle + zip
pyinstaller("path/to/usecli.config.toml")  # or point at a specific config
```

Output lands in `dist/` — `dist/mycli` for `onefile`, or a `dist/mycli/` folder
containing the executable (plus `_internal/` with the bundled assets) for
`onedir`. With `zip=True`, a `dist/mycli.zip` archive is created alongside the
folder. `make:bundle` and `usecli-bundle` are only available when PyInstaller
is installed.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- DEVELOPMENT -->

## Development

See the [Development Guide](https://github.com/thememium/usecli/blob/master/docs/development.md) for setup, testing, and architecture details.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->

## Contributing

Read the [Contributing Guide](https://github.com/thememium/usecli/blob/master/.github/contributing.md).

Quick workflow:

1. Fork and branch: `git checkout -b feature/name`
2. Make changes
3. Run checks: `uv run poe clean-full`
4. Commit and push
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->

## License

MIT. See `LICENSE`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<div align="center">
  <p>
    <sub>Built by <a href="https://github.com/thememium">thememium</a></sub>
  </p>
</div>
