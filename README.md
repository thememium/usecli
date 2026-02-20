<a name="readme-top"></a>

<!-- PROJECT LOGO -->
<div align="center">
  <a href="https://github.com/thememium/usecli">
    <img src="docs/images/usecli-logo.png" alt="useCli" width="360" height="162">
  </a>

  <!-- <h3 align="center">useCli</h3> -->

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
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#features">Features</a></li>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li>
      <a href="#usage">Usage</a>
      <ul>
        <li><a href="#create-your-own-cli">Create Your Own CLI</a></li>
        <li><a href="#available-commands">Available Commands</a></li>
        <li><a href="#hide-default-commands">Hide Default Commands</a></li>
        <li><a href="#prefix-matching">Prefix Matching</a></li>
        <li><a href="#interactive-mode">Interactive Mode</a></li>
        <li><a href="#creating-new-commands">Creating New Commands</a></li>
        <li><a href="#command-structure">Command Structure</a></li>
        <li><a href="#nested-commands">Nested Commands</a></li>
        <li><a href="#grouped-commands">Grouped Commands</a></li>
        <li><a href="#ui-components">UI Components</a></li>
        <li><a href="#global-flags">Global Flags</a></li>
      </ul>
    </li>
    <li>
      <a href="#development">Development</a>
      <ul>
        <li><a href="#poe-tasks">Poe Tasks</a></li>
        <li><a href="#testing">Testing</a></li>
        <li><a href="#code-quality">Code Quality</a></li>
        <li><a href="#architecture">Architecture</a></li>
      </ul>
    </li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
  </ol>
</details>

<!-- ABOUT THE PROJECT -->

## About The Project

useCli is a CLI framework for Python built on Typer and Click. It handles the repetitive parts of CLI development—command routing, help formatting, interactive menus, and error handling—so you can focus on writing command logic.

<a name="features"></a>

### Features

- Prefix matching for quick command execution (`he` → `help`)
- Terminal UI components: styled output, interactive menus, prompts, and confirmations
- Command scaffolding with `make:command`
- Nested command groups (e.g., `spec show`, `change list`)
- Styled error messages with custom exception classes
- Full type hints throughout

### Built With

- **Typer**: CLI framework built on Click
- **Click**: Command-line interface creation kit
- **Rich**: Terminal formatting and styling
- **fzf-bin**: Fuzzy finder for interactive mode
- **simple-term-menu**: Terminal menus
- **Jinja2**: Command template scaffolding
- **PyFiglet**: ASCII art banners
- **PyYAML**: Configuration file support

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->

## Getting Started

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Installation

#### Add as a Dependency

To add usecli to your project's dependencies:

```sh
uv add "usecli @ git+https://github.com/thememium/usecli.git"
```

Or with pip:

```sh
pip install git+https://github.com/thememium/usecli.git
```



<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE -->

## Usage

### Create Your Own CLI

Initialize a new CLI in your project:

```sh
usecli init
```

You'll be prompted for:
- CLI title
- Description
- Commands directory
- Entry point name

This creates the commands package, writes a useCli config (`[tool.usecli]` in `pyproject.toml` or `usecli.config.toml`), and sets up `[project.scripts]` to point to `usecli:run_app`.

After init, run your CLI (default name is `usecli`):

```sh
usecli make:command mycommand
```

### Available Commands

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COMMANDS                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Core Commands:                                                             │
│    about              Display detailed information about the application    │
│    help               Show help information                                 │
│    init               Initialize usecli in the current project              │
│    inspire            Display an inspirational quote                        │
│                                                                             │
│  Development:                                                               │
│    make:command       Create a new CLI command                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

Run any command with `--help` for detailed usage.

### Hide Default Commands

You can hide the built-in commands individually using config flags in
`pyproject.toml` (recommended) or `usecli.config.toml`:

```toml
[tool.usecli]
hide_init = true
hide_inspire = true
hide_make_command = false
```

### Prefix Matching

Type partial command names:

```sh
usecli he          # Runs 'help'
usecli ab          # Runs 'about'
usecli ma:co       # Runs 'make:command'
```

If multiple commands match, a filtered list is shown.

### Interactive Mode

Add `--interactive` (or `-i`) to any command to open the interactive runner:

```sh
usecli --interactive
usecli help --interactive
usecli make:command --interactive
```

### Creating New Commands

Generate a command scaffold:

```sh
usecli make:command mycommand
```

This creates a command file with:

```python
from usecli import Argument, BaseCommand, Option, Prompt, console


class MycommandCommand(BaseCommand):
    def signature(self) -> str:
        return "mycommand"

    def description(self) -> str:
        return "Description of mycommand"

    def handle(
        self,
        name: str = Argument(..., help="Your name"),
        greeting: str = Option("Hello", "--greeting", "-g", help="Greeting to use"),
    ) -> None:
        console.print(f"[bold green]{greeting}, {name}![/bold green]")

        favorite = Prompt.ask(
            "What's your favorite color?",
            choices=["red", "green", "blue"],
        )
        console.print(f"You chose: {favorite}")
```

### Command Structure

All commands extend `BaseCommand` and implement three methods:

- `signature()` — Returns the command name (e.g., `mycommand` or `group:subcommand`)
- `description()` — Returns the help text
- `handle()` — Contains the command logic

Optionally, override `visible()` to hide commands from the command list:

```python
def visible(self) -> bool:
    return False  # Hidden from 'help' output
```

### Nested Commands

Create command groups with space-separated signatures:

```python
def signature(self) -> str:
    return "spec show"  # Creates 'spec' group with 'show' subcommand
```

These work alongside colon-separated commands like `make:command`.

### Grouped Commands

Commands with colons in their names are automatically grouped in the help output:

```python
class DatabaseBackupCommand(BaseCommand):
    def signature(self) -> str:
        return "db:backup"

class DatabaseRestoreCommand(BaseCommand):
    def signature(self) -> str:
        return "db:restore"

class DatabaseMigrateCommand(BaseCommand):
    def signature(self) -> str:
        return "db:migrate"
```

This displays in help as:

```
db:
  backup              Backup the database
  migrate             Run database migrations
  restore             Restore the database
```

Colon-separated commands (`group:action`) are grouped by their prefix, while space-separated commands (`group action`) create nested subcommand groups.

### UI Components

Import from `usecli`:

```python
from usecli import console, Prompt, Confirm, Menu, Argument, Option
```

**Console**: Styled output via Rich
```python
console.print("[green]Success![/green]")
```

**Prompt**: Interactive prompts
```python
name = Prompt.ask("Enter your name")
value = Prompt.ask("Select one", choices=["a", "b", "c"])
```

**Confirm**: Yes/no questions
```python
if Confirm.ask("Continue?"):
    pass
```

**Menu**: Terminal selection menus
```python
menu = Menu(["Option 1", "Option 2", "Option 3"])
selection = menu.show()
```

### Global Flags

```sh
usecli --version      # Show version
usecli -v             # Short form
usecli --help         # Show help
usecli -h             # Short form
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- DEVELOPMENT -->

## Development

### Poe Tasks

This project uses `poe` for task management. Available tasks:

| Task | Description |
|------|-------------|
| `uv run poe dev` | Run the CLI application |
| `uv run poe clean` | Run isort and ruff format |
| `uv run poe clean-full` | Run isort, ruff check/fix, ruff format, deptry, and ty check |
| `uv run poe sort` | Run isort |
| `uv run poe lint` | Run ruff linter with auto-fix |
| `uv run poe format` | Run ruff formatter |
| `uv run poe test` | Run pytest test suite |
| `uv run poe deptry` | Check for dependency issues |
| `uv run poe typecheck` | Run ty type checker |

### Testing

Run the test suite:

```sh
uv run poe test
```

Or with verbose output:

```sh
uv run pytest tests/ -v
```

### Code Quality

Format and lint code:

```sh
uv run poe clean-full
```

Individual tools:

```sh
# Sort imports
uv run poe sort

# Lint code
uv run poe lint

# Format code
uv run poe format

# Type check
uv run poe typecheck

# Check dependencies
uv run poe deptry
```

### Architecture

#### Core Components

- **BaseCommand**: Abstract base class for all commands
- **CommandService**: Discovers and loads commands from directories
- **PrefixMatchingGroup**: Typer group with prefix matching support
- **COLOR**: Semantic color constants (PRIMARY, SECONDARY, SUCCESS, ERROR, WARNING, OPTION)

#### Command Structure

```python
class MyCommand(BaseCommand):
    def signature(self) -> str:
        return "my:command"

    def description(self) -> str:
        return "What this command does"

    def handle(self, *args, **kwargs) -> None:
        pass
```

#### Directory Layout

**Source Code Structure:**

```
src/usecli/
├── __init__.py                    # Main entry point
├── cli/
│   ├── commands/                  # Command implementations
│   │   ├── defaults/             # Built-in commands
│   │   │   ├── base/             # Core commands (about, help, inspire)
│   │   │   ├── core/             # Utility commands
│   │   │   └── make/             # Code generation commands
│   │   └── custom/               # User-defined commands
│   ├── config/                   # Color system and configuration
│   ├── core/                     # BaseCommand, error handling, validators
│   ├── services/                 # Command loading service
│   ├── templates/                # Jinja2 templates for scaffolding
│   └── utils/                    # Interactive utilities
└── shared/                       # Global configuration
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->

## Contributing

Contributions are welcome! Please read the [Contributing Guide](.github/contributing.md) for detailed information on:

- Development setup
- Code quality requirements
- Pull request expectations
- Style guidelines

Quick start:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Make your changes
4. Run tests and ensure code quality (`uv run poe clean-full`)
5. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
6. Push to the branch (`git push origin feature/AmazingFeature`)
7. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->

## License

Distributed under the MIT License. See `LICENSE` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

<div align="center">
  <p>
    <sub>Built with ❤️ by <a href="https://github.com/thememium">thememium</a></sub>
  </p>
</div>
