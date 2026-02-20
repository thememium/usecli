# Development Guide

This guide is for contributors or those extending useCli.

## Quick Start

1. Fork the repository
2. Clone your fork
3. Install dependencies: `uv sync`
4. Run tests: `uv run poe test`

## Poe Tasks

This project uses `poe` for task management:

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

## Testing

Run the test suite:

```sh
uv run poe test
```

With verbose output:

```sh
uv run pytest tests/ -v
```

## Code Quality

Format and lint:

```sh
uv run poe clean-full
```

Individual tools:

```sh
# Sort imports
uv run poe sort

# Lint
uv run poe lint

# Format
uv run poe format

# Type check
uv run poe typecheck

# Check dependencies
uv run poe deptry
```

## Architecture

### Core Components

- **BaseCommand**: Abstract base class for all commands
- **CommandService**: Discovers and loads commands from directories
- **PrefixMatchingGroup**: Typer group with prefix matching support
- **COLOR**: Semantic color constants (PRIMARY, SECONDARY, SUCCESS, ERROR, WARNING, OPTION)

### Command Structure

```python
class MyCommand(BaseCommand):
    def signature(self) -> str:
        return "my:command"

    def description(self) -> str:
        return "What this command does"

    def handle(self, *args, **kwargs) -> None:
        pass
```

### Directory Layout

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

## Contributing

Contributions are welcome! Please read the [Contributing Guide](../.github/contributing.md) for details on:

- Development setup
- Code quality requirements
- Pull request expectations
- Style guidelines

Quick workflow:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Make your changes
4. Run tests and code quality checks (`uv run poe clean-full`)
5. Commit (`git commit -m 'Add some AmazingFeature'`)
6. Push (`git push origin feature/AmazingFeature`)
7. Open a Pull Request
