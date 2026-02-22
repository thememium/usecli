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

### UI Components

```python
from usecli import console, Prompt, Confirm, Menu

console.print("[green]Done![/green]")
name = Prompt.ask("Enter name")
ok = Confirm.ask("Continue?")
choice = Menu(["A", "B", "C"]).show()
```

### Available Commands

```
about        Show app info
help         Show help
init         Initialize usecli
inspire      Random quote
make:command Create new command
```

### Hiding Built-in Commands

```toml
[tool.usecli]
hide_init = true
hide_inspire = true
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
