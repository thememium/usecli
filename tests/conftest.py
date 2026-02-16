"""Test configuration and shared fixtures for usecli CLI tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# =============================================================================
# Rich Console Fixtures
# =============================================================================


@pytest.fixture
def mock_console():
    """Fixture providing a mocked Rich Console."""
    with patch("rich.console.Console") as mock:
        console_instance = Mock()
        console_instance.print = Mock()
        console_instance.rule = Mock()
        mock.return_value = console_instance
        yield console_instance


@pytest.fixture
def mock_stderr_console():
    """Fixture providing a mocked Rich Console that writes to stderr."""
    with patch("rich.console.Console") as mock:
        console_instance = Mock()
        console_instance.print = Mock()
        console_instance.rule = Mock()
        mock.return_value = console_instance
        yield console_instance


# =============================================================================
# Click/Typer Fixtures
# =============================================================================


@pytest.fixture
def mock_click_context():
    """Fixture providing a mocked Click context."""
    ctx = MagicMock()
    ctx.get_help = Mock(return_value="Mocked help text")
    ctx.obj = {}
    return ctx


@pytest.fixture
def mock_typer_app():
    """Fixture providing a mocked Typer app."""
    app = MagicMock()
    app.registered_commands = []
    app.command = Mock(return_value=lambda f: f)
    return app


@pytest.fixture
def mock_typer_context():
    """Fixture providing a mocked Typer context."""
    ctx = MagicMock()
    ctx.invoked_subcommand = None
    ctx.obj = {}
    return ctx


# =============================================================================
# File System Fixtures
# =============================================================================


@pytest.fixture
def temp_file(tmp_path):
    """Fixture providing a temporary file path."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("test content")
    return str(file_path)


@pytest.fixture
def temp_dir(tmp_path):
    """Fixture providing a temporary directory path."""
    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    return str(dir_path)


@pytest.fixture
def mock_pyproject_toml(tmp_path):
    """Fixture providing a mock pyproject.toml file."""
    toml_content = b"""
[project]
name = "test-project"
version = "1.0.0"
description = "Test project"
"""
    toml_path = tmp_path / "pyproject.toml"
    toml_path.write_bytes(toml_content)
    return str(toml_path)


# =============================================================================
# Command Service Fixtures
# =============================================================================


@pytest.fixture
def mock_command_service():
    """Fixture providing a mocked CommandService."""
    with patch("usecli.cli.services.command_service.CommandService") as mock:
        service_instance = Mock()
        service_instance.version = "1.0.0"
        service_instance.commands = []
        service_instance.load_commands = Mock()
        mock.return_value = service_instance
        yield service_instance


# =============================================================================
# Terminal Menu Fixtures
# =============================================================================


@pytest.fixture
def mock_terminal_menu():
    """Fixture providing a mocked TerminalMenu."""
    with patch("simple_term_menu.TerminalMenu") as mock:
        menu_instance = Mock()
        menu_instance.show = Mock(return_value=0)
        mock.return_value = menu_instance
        yield menu_instance


# =============================================================================
# Rich Prompt Fixtures
# =============================================================================


@pytest.fixture
def mock_confirm_yes():
    """Fixture mocking Rich Confirm.ask to return True."""
    with patch("rich.prompt.Confirm.ask", return_value=True) as mock:
        yield mock


@pytest.fixture
def mock_confirm_no():
    """Fixture mocking Rich Confirm.ask to return False."""
    with patch("rich.prompt.Confirm.ask", return_value=False) as mock:
        yield mock


# =============================================================================
# Import/Module Fixtures
# =============================================================================


@pytest.fixture
def mock_importlib():
    """Fixture mocking importlib functions."""
    with (
        patch("importlib.util.spec_from_file_location") as mock_spec,
        patch("importlib.util.module_from_spec") as mock_module,
    ):
        spec = Mock()
        module = Mock()
        spec.loader = Mock()
        mock_spec.return_value = spec
        mock_module.return_value = module
        yield {
            "spec_from_file_location": mock_spec,
            "module_from_spec": mock_module,
            "spec": spec,
            "module": module,
        }


# =============================================================================
# Exception Testing Helper
# =============================================================================


class RaisesContext:
    """Helper class for testing exceptions with additional checks."""

    def __init__(self, expected_exception, match=None, check_message=True):
        self.expected_exception = expected_exception
        self.match = match
        self.check_message = check_message
        self.exception = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            raise AssertionError(
                f"Expected {self.expected_exception.__name__} but no exception was raised"
            )

        if not issubclass(exc_type, self.expected_exception):
            return False

        self.exception = exc_val

        if self.match and self.check_message:
            if self.match not in str(exc_val):
                raise AssertionError(
                    f"Expected exception message to contain '{self.match}', "
                    f"but got '{str(exc_val)}'"
                )

        return True


@pytest.fixture
def assert_raises():
    """Fixture providing enhanced assert_raises helper."""
    return RaisesContext
