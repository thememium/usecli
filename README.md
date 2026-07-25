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
    return "spec show"   # usecli spec show
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
```

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
