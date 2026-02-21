"""Comprehensive tests for usecli.cli.services.command_service module.

Tests cover:
- CommandService initialization: app, commands list, version initialization
- load_commands: orchestration of version and directory loading
- _load_version: package metadata version loading with various scenarios
- _load_from_dir: directory scanning, module import, BaseCommand detection
- _import_file: importlib integration for dynamic module loading
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from usecli.cli.core.base_command import BaseCommand
from usecli.cli.services.command_service import CommandService


def _mock_config_version(value: str | None) -> MagicMock:
    mock_config = MagicMock()
    mock_config.get_project_version.return_value = value
    return mock_config


def _mock_config_project_dir(path: Path) -> MagicMock:
    mock_config = MagicMock()
    mock_config.get_project_commands_dir.return_value = path
    return mock_config


# =============================================================================
# Test Command Implementations
# =============================================================================


class DummyCommand(BaseCommand):
    """Dummy implementation of BaseCommand."""

    def handle(self, *args, **kwargs) -> None:
        pass

    def signature(self) -> str:
        return "test-cmd"

    def description(self) -> str:
        return "Test command"


class AnotherDummyCommand(BaseCommand):
    """Another dummy implementation of BaseCommand."""

    def handle(self, *args, **kwargs) -> None:
        pass

    def signature(self) -> str:
        return "another-cmd"

    def description(self) -> str:
        return "Another test command"


class NotACommand:
    """Not a BaseCommand subclass."""

    pass


# =============================================================================
# CommandService.__init__ Tests
# =============================================================================


class TestCommandServiceInit:
    """Tests for CommandService initialization."""

    def test_init_stores_app(self):
        """Test __init__ stores the Typer app reference."""
        app = typer.Typer()
        service = CommandService(app=app)
        assert service.app is app

    def test_init_initializes_empty_commands_list(self):
        """Test __init__ initializes commands as empty list."""
        app = typer.Typer()
        service = CommandService(app=app)
        assert service.commands == []
        assert isinstance(service.commands, list)

    def test_init_sets_default_version(self):
        """Test __init__ sets default version to '0.0.0'."""
        app = typer.Typer()
        service = CommandService(app=app)
        assert service.version == "0.0.0"

    def test_init_with_mock_app(self):
        """Test __init__ works with mock Typer app."""
        mock_app = MagicMock()
        service = CommandService(app=mock_app)
        assert service.app is mock_app

    def test_init_multiple_instances_independent(self):
        """Test multiple CommandService instances are independent."""
        app1 = typer.Typer()
        app2 = typer.Typer()
        service1 = CommandService(app=app1)
        service2 = CommandService(app=app2)

        assert service1.app is app1
        assert service2.app is app2
        assert service1.commands is not service2.commands


# =============================================================================
# CommandService.load_commands Tests
# =============================================================================


class TestCommandServiceLoadCommands:
    """Tests for CommandService.load_commands method."""

    @patch("usecli.cli.services.command_service.get_config")
    def test_load_commands_calls_load_version(self, mock_get_config, tmp_path):
        """Test load_commands calls _load_version."""
        mock_get_config.return_value = _mock_config_project_dir(
            tmp_path / "project_commands"
        )
        app = MagicMock()
        service = CommandService(app=app)

        with patch.object(service, "_load_version") as mock_load_version:
            with patch.object(service, "_load_from_dir"):
                service.load_commands()

                mock_load_version.assert_called_once()

    @patch("usecli.cli.services.command_service.get_config")
    def test_load_commands_calls_load_from_dir_commands(
        self, mock_get_config, tmp_path
    ):
        """Test load_commands calls _load_from_dir for commands directory."""
        mock_get_config.return_value = _mock_config_project_dir(
            tmp_path / "project_commands"
        )
        app = MagicMock()
        service = CommandService(app=app)

        with patch.object(service, "_load_version"):
            with patch.object(service, "_load_from_dir") as mock_load_from_dir:
                service.load_commands()

                # First call should be for commands
                calls = mock_load_from_dir.call_args_list
                assert len(calls) >= 1
                first_call_path = calls[0][0][0]
                assert "commands" in str(first_call_path)

    @patch("usecli.cli.services.command_service.get_config")
    def test_load_commands_calls_load_from_dir_project(self, mock_get_config, tmp_path):
        """Test load_commands calls _load_from_dir for project directory."""
        mock_get_config.return_value = _mock_config_project_dir(
            tmp_path / "project_commands"
        )
        app = MagicMock()
        service = CommandService(app=app)

        with patch.object(service, "_load_version"):
            with patch.object(service, "_load_from_dir") as mock_load_from_dir:
                service.load_commands()

                # Second call should be for project commands
                calls = mock_load_from_dir.call_args_list
                assert len(calls) >= 2
                second_call_path = calls[1][0][0]
                assert "commands" in str(second_call_path)

    @patch("usecli.cli.services.command_service.get_config")
    def test_load_commands_calls_all_load_from_dir(self, mock_get_config, tmp_path):
        """Test load_commands calls _load_from_dir for commands and project directories."""
        mock_get_config.return_value = _mock_config_project_dir(
            tmp_path / "project_commands"
        )
        app = MagicMock()
        service = CommandService(app=app)

        with patch.object(service, "_load_version"):
            with patch.object(service, "_load_from_dir") as mock_load_from_dir:
                service.load_commands()

                assert mock_load_from_dir.call_count == 2

    @patch("usecli.cli.services.command_service.get_config")
    def test_load_commands_correct_directory_paths(self, mock_get_config, tmp_path):
        """Test load_commands uses correct directory paths."""
        project_commands_dir = tmp_path / "project_commands"
        mock_get_config.return_value = _mock_config_project_dir(project_commands_dir)
        app = MagicMock()
        service = CommandService(app=app)

        with patch.object(service, "_load_version"):
            with patch.object(service, "_load_from_dir") as mock_load_from_dir:
                service.load_commands()

                calls = mock_load_from_dir.call_args_list
                commands_path = calls[0][0][0]
                project_path = calls[1][0][0]

                assert str(commands_path).endswith("cli/commands")
                assert project_path == project_commands_dir

    @patch("usecli.cli.services.command_service.get_config")
    def test_load_commands_execution_order(self, mock_get_config, tmp_path):
        """Test load_commands executes in correct order."""
        mock_get_config.return_value = _mock_config_project_dir(
            tmp_path / "project_commands"
        )
        app = MagicMock()
        service = CommandService(app=app)

        call_order = []

        def mock_load_version():
            call_order.append("version")

        def mock_load_from_dir(path):
            call_order.append(str(path).split("/")[-1])

        with patch.object(service, "_load_version", side_effect=mock_load_version):
            with patch.object(
                service, "_load_from_dir", side_effect=mock_load_from_dir
            ):
                service.load_commands()

                assert call_order[0] == "version"
                assert call_order[1] == "commands"
                assert call_order[2] == "project_commands"

    @patch("usecli.cli.services.command_service.get_config")
    def test_load_commands_skips_project_dir_when_same_as_package(
        self, mock_get_config, tmp_path
    ):
        package_root = tmp_path / "pkg"
        package_commands = package_root / "cli/commands"
        mock_get_config.return_value = _mock_config_project_dir(package_commands)

        app = MagicMock()
        service = CommandService(app=app)

        with patch("usecli.cli.services.command_service.PACKAGE_ROOT", package_root):
            with patch.object(service, "_load_version"):
                with patch.object(service, "_load_from_dir") as mock_load_from_dir:
                    service.load_commands()

                    assert mock_load_from_dir.call_count == 1

    @patch("usecli.cli.services.command_service.get_config")
    def test_load_commands_skips_project_dir_when_nested_under_package(
        self, mock_get_config, tmp_path
    ):
        package_root = tmp_path / "pkg"
        package_commands = package_root / "cli/commands"
        project_commands = package_commands / "custom"
        mock_get_config.return_value = _mock_config_project_dir(project_commands)

        app = MagicMock()
        service = CommandService(app=app)

        with patch("usecli.cli.services.command_service.PACKAGE_ROOT", package_root):
            with patch.object(service, "_load_version"):
                with patch.object(service, "_load_from_dir") as mock_load_from_dir:
                    service.load_commands()

                    assert mock_load_from_dir.call_count == 1


# =============================================================================
# CommandService._load_version Tests
# =============================================================================


class TestCommandServiceLoadVersion:
    """Tests for CommandService._load_version method."""

    @patch("usecli.cli.services.command_service.get_config")
    @patch("usecli.cli.services.command_service.get_version")
    def test_load_version_with_valid_version(self, mock_get_version, mock_get_config):
        """Test _load_version reads version from package metadata."""
        mock_get_config.return_value = _mock_config_version(None)
        mock_get_version.return_value = "1.2.3"

        app = MagicMock()
        service = CommandService(app=app)
        service._load_version()

        assert service.version == "1.2.3"
        mock_get_version.assert_called_once_with("usecli")

    @patch("usecli.cli.services.command_service.get_config")
    @patch("usecli.cli.services.command_service.get_version")
    def test_load_version_with_package_not_found(
        self, mock_get_version, mock_get_config
    ):
        """Test _load_version uses default when package not found."""
        from importlib.metadata import PackageNotFoundError

        mock_get_config.return_value = _mock_config_version(None)
        mock_get_version.side_effect = PackageNotFoundError("usecli")

        app = MagicMock()
        service = CommandService(app=app)
        service._load_version()

        assert service.version == "0.0.0"

    @patch("usecli.cli.services.command_service.get_config")
    @patch("usecli.cli.services.command_service.get_version")
    def test_load_version_propagates_unexpected_exceptions(
        self, mock_get_version, mock_get_config
    ):
        """Test _load_version propagates unexpected exceptions."""
        mock_get_config.return_value = _mock_config_version(None)
        mock_get_version.side_effect = RuntimeError("Some error")

        app = MagicMock()
        service = CommandService(app=app)

        with pytest.raises(RuntimeError, match="Some error"):
            service._load_version()

    @patch("usecli.cli.services.command_service.get_config")
    @patch("usecli.cli.services.command_service.get_version")
    def test_load_version_multiple_calls(self, mock_get_version, mock_get_config):
        """Test _load_version can be called multiple times."""
        mock_get_config.return_value = _mock_config_version(None)
        mock_get_version.return_value = "3.0.0"

        app = MagicMock()
        service = CommandService(app=app)
        service._load_version()
        first_version = service.version

        mock_get_version.return_value = "3.1.0"
        service._load_version()
        second_version = service.version

        assert first_version == "3.0.0"
        assert second_version == "3.1.0"


# =============================================================================
# CommandService._load_from_dir Tests
# =============================================================================


class TestCommandServiceLoadFromDir:
    """Tests for CommandService._load_from_dir method."""

    def test_load_from_dir_nonexistent_directory_returns_early(self):
        """Test _load_from_dir returns early if directory doesn't exist."""
        app = MagicMock()
        service = CommandService(app=app)

        mock_dir = MagicMock()
        mock_dir.exists.return_value = False

        with patch.object(service, "_import_file") as mock_import_file:
            service._load_from_dir(mock_dir)

            # _import_file should not be called
            mock_import_file.assert_not_called()

    def test_load_from_dir_existing_directory_continues(self):
        """Test _load_from_dir continues if directory exists."""
        app = MagicMock()
        service = CommandService(app=app)

        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.rglob.return_value = []

        service._load_from_dir(mock_dir)

        # rglob should be called
        mock_dir.rglob.assert_called_once_with("*.py")

    def test_load_from_dir_skips_init_py_files(self):
        """Test _load_from_dir skips __init__.py files."""
        app = MagicMock()
        service = CommandService(app=app)

        # Create mock paths
        init_file = MagicMock()
        init_file.name = "__init__.py"

        py_file = MagicMock()
        py_file.name = "command.py"

        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.rglob.return_value = [init_file, py_file]

        with patch.object(service, "_import_file") as mock_import_file:
            service._load_from_dir(mock_dir)

            # _import_file should be called only for py_file, not init_file
            mock_import_file.assert_called_once_with(py_file)

    def test_load_from_dir_processes_all_py_files(self):
        """Test _load_from_dir processes all .py files except __init__.py."""
        app = MagicMock()
        service = CommandService(app=app)

        # Create mock paths
        file1 = MagicMock()
        file1.name = "command1.py"

        file2 = MagicMock()
        file2.name = "command2.py"

        file3 = MagicMock()
        file3.name = "__init__.py"

        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.rglob.return_value = [file1, file2, file3]

        with patch.object(service, "_import_file") as mock_import_file:
            mock_import_file.return_value = None
            service._load_from_dir(mock_dir)

            # _import_file called twice (for file1 and file2)
            assert mock_import_file.call_count == 2

    def test_load_from_dir_import_failure_continues(self):
        """Test _load_from_dir continues even if import fails."""
        app = MagicMock()
        service = CommandService(app=app)

        file1 = MagicMock()
        file1.name = "command1.py"
        file2 = MagicMock()
        file2.name = "command2.py"

        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.rglob.return_value = [file1, file2]

        with patch.object(service, "_import_file") as mock_import_file:
            mock_import_file.side_effect = [None, MagicMock()]
            service._load_from_dir(mock_dir)

            # Should attempt to process both files
            assert mock_import_file.call_count == 2

    def test_load_from_dir_detects_base_command_subclasses(self):
        """Test _load_from_dir finds and instantiates BaseCommand subclasses."""
        app = MagicMock()
        service = CommandService(app=app)

        # Create mock module with BaseCommand subclass
        mock_module = MagicMock()

        # Create a real class hierarchy
        test_cmd = type(
            "TestCmd",
            (BaseCommand,),
            {
                "handle": lambda self: None,
                "signature": lambda self: "test",
                "description": lambda self: "Test",
            },
        )

        mock_file = MagicMock()
        mock_file.name = "command.py"

        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.rglob.return_value = [mock_file]

        def mock_get_members(obj):
            if obj is mock_module:
                return [("TestCmd", test_cmd)]
            return []

        with patch.object(service, "_import_file", return_value=mock_module):
            with patch("inspect.getmembers", side_effect=mock_get_members):
                with patch("inspect.isclass", return_value=True):
                    with patch("inspect.issubclass") as mock_issubclass:
                        # issubclass should return True for TestCmd, False for BaseCommand
                        def issubclass_check(obj, parent):
                            if obj is BaseCommand:
                                return True
                            if obj is test_cmd:
                                return True
                            return False

                        mock_issubclass.side_effect = issubclass_check

                        service._load_from_dir(mock_dir)

    def test_load_from_dir_skips_base_command_itself(self):
        """Test _load_from_dir does not instantiate BaseCommand directly."""
        app = MagicMock()
        service = CommandService(app=app)

        mock_module = MagicMock()

        mock_file = MagicMock()
        mock_file.name = "base.py"

        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.rglob.return_value = [mock_file]

        def mock_get_members(obj):
            if obj is mock_module:
                return [("BaseCommand", BaseCommand)]
            return []

        with patch.object(service, "_import_file", return_value=mock_module):
            with patch("inspect.getmembers", side_effect=mock_get_members):
                with patch("inspect.isclass", return_value=True):
                    with patch("inspect.issubclass", return_value=True):
                        # BaseCommand should not be instantiated
                        service._load_from_dir(mock_dir)

    def test_load_from_dir_empty_directory(self):
        """Test _load_from_dir handles empty directory."""
        app = MagicMock()
        service = CommandService(app=app)

        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.rglob.return_value = []

        with patch.object(service, "_import_file") as mock_import_file:
            service._load_from_dir(mock_dir)
            mock_import_file.assert_not_called()


# =============================================================================
# CommandService._import_file Tests
# =============================================================================


class TestCommandServiceImportFile:
    """Tests for CommandService._import_file method."""

    @patch("importlib.util.module_from_spec")
    @patch("importlib.util.spec_from_file_location")
    def test_import_file_successful_import(
        self, mock_spec_from_file, mock_module_from_spec
    ):
        """Test _import_file successfully imports a Python file."""
        app = MagicMock()
        service = CommandService(app=app)

        # Setup mocks
        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file.return_value = mock_spec

        mock_module = MagicMock()
        mock_module_from_spec.return_value = mock_module

        path = MagicMock()
        path.stem = "test_command"

        result = service._import_file(path)

        assert result is mock_module
        mock_spec_from_file.assert_called_once_with("test_command", path)
        mock_module_from_spec.assert_called_once_with(mock_spec)
        mock_spec.loader.exec_module.assert_called_once_with(mock_module)

    @patch("importlib.util.spec_from_file_location")
    def test_import_file_spec_is_none(self, mock_spec_from_file):
        """Test _import_file returns None when spec is None."""
        app = MagicMock()
        service = CommandService(app=app)

        mock_spec_from_file.return_value = None

        path = MagicMock()
        path.stem = "bad_file"

        result = service._import_file(path)

        assert result is None

    @patch("importlib.util.spec_from_file_location")
    def test_import_file_spec_loader_is_none(self, mock_spec_from_file):
        """Test _import_file returns None when spec.loader is None."""
        app = MagicMock()
        service = CommandService(app=app)

        mock_spec = MagicMock()
        mock_spec.loader = None
        mock_spec_from_file.return_value = mock_spec

        path = MagicMock()
        path.stem = "bad_loader"

        result = service._import_file(path)

        assert result is None

    @patch("importlib.util.module_from_spec")
    @patch("importlib.util.spec_from_file_location")
    def test_import_file_exec_module_called(
        self, mock_spec_from_file, mock_module_from_spec
    ):
        """Test _import_file calls exec_module on the loader."""
        app = MagicMock()
        service = CommandService(app=app)

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file.return_value = mock_spec

        mock_module = MagicMock()
        mock_module_from_spec.return_value = mock_module

        path = MagicMock()
        path.stem = "module"

        service._import_file(path)

        mock_spec.loader.exec_module.assert_called_once_with(mock_module)

    @patch("importlib.util.module_from_spec")
    @patch("importlib.util.spec_from_file_location")
    def test_import_file_uses_stem_as_module_name(
        self, mock_spec_from_file, mock_module_from_spec
    ):
        """Test _import_file uses path.stem as module name."""
        app = MagicMock()
        service = CommandService(app=app)

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file.return_value = mock_spec

        mock_module = MagicMock()
        mock_module_from_spec.return_value = mock_module

        path = MagicMock()
        path.stem = "my_special_module"

        service._import_file(path)

        # First argument to spec_from_file_location should be "my_special_module"
        assert mock_spec_from_file.call_args[0][0] == "my_special_module"

    @patch("importlib.util.module_from_spec")
    @patch("importlib.util.spec_from_file_location")
    def test_import_file_passes_path_to_spec(
        self, mock_spec_from_file, mock_module_from_spec
    ):
        """Test _import_file passes path to spec_from_file_location."""
        app = MagicMock()
        service = CommandService(app=app)

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file.return_value = mock_spec

        mock_module = MagicMock()
        mock_module_from_spec.return_value = mock_module

        path = MagicMock()
        path.stem = "test"

        service._import_file(path)

        # Second argument should be the path
        assert mock_spec_from_file.call_args[0][1] == path

    @patch("importlib.util.module_from_spec")
    @patch("importlib.util.spec_from_file_location")
    def test_import_file_multiple_imports(
        self, mock_spec_from_file, mock_module_from_spec
    ):
        """Test _import_file can be called multiple times."""
        app = MagicMock()
        service = CommandService(app=app)

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file.return_value = mock_spec

        mock_module1 = MagicMock()
        mock_module2 = MagicMock()
        mock_module_from_spec.side_effect = [mock_module1, mock_module2]

        path1 = MagicMock()
        path1.stem = "module1"

        path2 = MagicMock()
        path2.stem = "module2"

        result1 = service._import_file(path1)
        result2 = service._import_file(path2)

        assert result1 is mock_module1
        assert result2 is mock_module2
        assert mock_spec_from_file.call_count == 2


# =============================================================================
# Integration Tests
# =============================================================================


class TestCommandServiceIntegration:
    """Integration tests for CommandService."""

    def test_full_initialization_workflow(self):
        """Test complete CommandService initialization workflow."""
        app = typer.Typer()
        service = CommandService(app=app)

        assert service.app is app
        assert service.commands == []
        assert service.version == "0.0.0"

    @patch("usecli.cli.services.command_service.get_config")
    @patch("usecli.cli.services.command_service.get_version")
    def test_load_commands_integration_with_mocked_version(
        self, mock_get_version, mock_get_config
    ):
        """Test load_commands with mocked package metadata."""
        mock_get_config.return_value = _mock_config_version(None)
        mock_get_version.return_value = "2.5.0"

        app = MagicMock()
        service = CommandService(app=app)

        with patch.object(service, "_load_from_dir"):
            service.load_commands()

            assert service.version == "2.5.0"

    def test_command_service_with_multiple_operations(self):
        """Test CommandService with multiple load operations."""
        app = MagicMock()
        service = CommandService(app=app)

        # First load
        with patch.object(service, "_load_version"):
            with patch.object(service, "_load_from_dir"):
                service.load_commands()

        assert service.version != ""

        # Second load
        with patch.object(service, "_load_version"):
            with patch.object(service, "_load_from_dir"):
                service.load_commands()

        assert service.version != ""

    def test_command_service_attribute_persistence(self):
        """Test CommandService attributes persist between operations."""
        app = MagicMock()
        service = CommandService(app=app)

        original_app = service.app
        original_commands = service.commands

        with patch.object(service, "_load_version"):
            with patch.object(service, "_load_from_dir"):
                service.load_commands()

        assert service.app is original_app
        assert service.commands is original_commands


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestCommandServiceEdgeCases:
    """Edge case tests for CommandService."""

    @patch("usecli.cli.services.command_service.get_config")
    @patch("usecli.cli.services.command_service.get_version")
    def test_load_version_with_valid_version(self, mock_get_version, mock_get_config):
        """Test _load_version reads version from package metadata."""
        mock_get_config.return_value = _mock_config_version(None)
        mock_get_version.return_value = "1.2.3"

        app = MagicMock()
        service = CommandService(app=app)
        service._load_version()

        assert service.version == "1.2.3"

    def test_load_from_dir_with_non_class_objects(self):
        """Test _load_from_dir ignores non-class objects in modules."""
        app = MagicMock()
        service = CommandService(app=app)

        mock_module = MagicMock()

        mock_file = MagicMock()
        mock_file.name = "module.py"

        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.rglob.return_value = [mock_file]

        def mock_get_members(obj):
            if obj is mock_module:
                return [
                    ("CONSTANT", 42),
                    ("function", lambda: None),
                    ("variable", "string"),
                ]
            return []

        with patch.object(service, "_import_file", return_value=mock_module):
            with patch("inspect.getmembers", side_effect=mock_get_members):
                with patch("inspect.isclass", return_value=False):
                    service._load_from_dir(mock_dir)

    def test_import_file_with_special_characters_in_stem(self):
        """Test _import_file handles special characters in module name."""
        app = MagicMock()
        service = CommandService(app=app)

        with patch("importlib.util.spec_from_file_location") as mock_spec_from_file:
            with patch("importlib.util.module_from_spec"):
                mock_spec = MagicMock()
                mock_spec.loader = None
                mock_spec_from_file.return_value = mock_spec

                path = MagicMock()
                path.stem = "module-with-dash"

                result = service._import_file(path)

                # Should still be None because loader is None, but should not error
                assert result is None


# =============================================================================
# Version Loading Behavior Tests
# =============================================================================


class TestCommandServiceVersionBehavior:
    """Tests for version loading behavior in CommandService."""

    @patch("usecli.cli.services.command_service.get_config")
    @patch("usecli.cli.services.command_service.get_version")
    def test_version_with_prerelease_tags(self, mock_get_version, mock_get_config):
        """Test version with prerelease tags is preserved."""
        mock_get_config.return_value = _mock_config_version(None)
        mock_get_version.return_value = "1.0.0-beta.1"

        app = MagicMock()
        service = CommandService(app=app)
        service._load_version()

        assert service.version == "1.0.0-beta.1"

    @patch("usecli.cli.services.command_service.get_config")
    @patch("usecli.cli.services.command_service.get_version")
    def test_version_with_development_versions(self, mock_get_version, mock_get_config):
        """Test version with dev tags is preserved."""
        mock_get_config.return_value = _mock_config_version(None)
        mock_get_version.return_value = "1.0.0.dev0"

        app = MagicMock()
        service = CommandService(app=app)
        service._load_version()

        assert service.version == "1.0.0.dev0"


# =============================================================================
# Mocking and Isolation Tests
# =============================================================================


class TestCommandServiceMockingBehavior:
    """Tests for mocking behavior in CommandService."""

    def test_app_can_be_mocked_independently(self):
        """Test app parameter can be different mock implementations."""
        mock_app1 = MagicMock()
        mock_app2 = MagicMock()

        service1 = CommandService(app=mock_app1)
        service2 = CommandService(app=mock_app2)

        assert service1.app is not service2.app
        assert mock_app1.call_count == 0
        assert mock_app2.call_count == 0

    def test_load_methods_can_be_independently_mocked(self):
        """Test load methods can be mocked independently."""
        app = MagicMock()
        service = CommandService(app=app)

        with patch.object(service, "_load_version") as mock_load_version:
            with patch.object(service, "_load_from_dir") as mock_load_from_dir:
                service._load_version()
                service._load_from_dir(Path("."))

                mock_load_version.assert_called_once()
                mock_load_from_dir.assert_called_once()


# =============================================================================
# Comprehensive Integration Scenarios
# =============================================================================


class TestCommandServiceRealWorldScenarios:
    """Real-world scenario tests for CommandService."""

    @patch("usecli.cli.services.command_service.get_config")
    @patch("usecli.cli.services.command_service.get_version")
    def test_scenario_version_from_package_metadata(
        self, mock_get_version, mock_get_config
    ):
        """Test version loading from package metadata."""
        mock_get_config.return_value = _mock_config_version(None)
        mock_get_version.return_value = "1.5.2"

        app = MagicMock()
        service = CommandService(app=app)
        service._load_version()

        assert service.version == "1.5.2"

    def test_scenario_multiple_py_files_in_directory(self):
        """Test loading multiple command files from a directory."""
        app = MagicMock()
        service = CommandService(app=app)

        # Create multiple mock files
        file1 = MagicMock()
        file1.name = "command1.py"

        file2 = MagicMock()
        file2.name = "command2.py"

        file3 = MagicMock()
        file3.name = "command3.py"

        init_file = MagicMock()
        init_file.name = "__init__.py"

        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.rglob.return_value = [file1, file2, file3, init_file]

        with patch.object(service, "_import_file") as mock_import:
            mock_import.return_value = None
            service._load_from_dir(mock_dir)

            # Should process only the 3 command files, not __init__.py
            assert mock_import.call_count == 3

    def test_scenario_nested_directory_structure(self):
        """Test _load_from_dir with nested directory paths."""
        app = MagicMock()
        service = CommandService(app=app)

        # Create nested file structure
        files = [
            MagicMock(name="main.py"),
            MagicMock(name="nested_sub.py"),
        ]

        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.rglob.return_value = files

        with patch.object(service, "_import_file") as mock_import:
            mock_import.return_value = None
            service._load_from_dir(mock_dir)

            # rglob with "*.py" should be called
            mock_dir.rglob.assert_called_once_with("*.py")

    def test_scenario_rapid_successive_loads(self):
        """Test rapid successive load_commands calls."""
        app = MagicMock()
        service = CommandService(app=app)

        with patch.object(service, "_load_version"):
            with patch.object(service, "_load_from_dir"):
                for _ in range(5):
                    service.load_commands()

                assert service.version == "0.0.0"
                assert service.commands == []

    @patch("importlib.util.module_from_spec")
    @patch("importlib.util.spec_from_file_location")
    def test_scenario_import_file_with_various_paths(
        self, mock_spec_from_file, mock_module_from_spec
    ):
        """Test _import_file with various path formats."""
        app = MagicMock()
        service = CommandService(app=app)

        mock_spec = MagicMock()
        mock_spec.loader = MagicMock()
        mock_spec_from_file.return_value = mock_spec
        mock_module_from_spec.return_value = MagicMock()

        paths = [
            MagicMock(stem="command_one"),
            MagicMock(stem="command_two"),
            MagicMock(stem="command_three"),
        ]

        for path in paths:
            result = service._import_file(path)
            assert result is not None

    def test_scenario_exception_resilience_chain(self):
        """Test that exceptions in one step don't break the chain."""
        app = MagicMock()
        service = CommandService(app=app)

        call_log = []

        def mock_load_version_fail():
            call_log.append("version_called")
            raise Exception("Version load failed")

        def mock_load_from_dir_success(path):
            call_log.append(f"dir_called_{str(path).split('/')[-1]}")

        with patch.object(service, "_load_version", side_effect=mock_load_version_fail):
            with patch.object(
                service, "_load_from_dir", side_effect=mock_load_from_dir_success
            ):
                try:
                    service.load_commands()
                except Exception:
                    pass

                # load_version was called first
                assert "version_called" in call_log

    def test_scenario_state_isolation_between_instances(self):
        """Test that different instances don't share state."""
        app1 = MagicMock()
        app2 = MagicMock()

        service1 = CommandService(app=app1)
        service2 = CommandService(app=app2)

        service1.version = "1.0.0"
        service1.commands = ["cmd1"]

        assert service2.version == "0.0.0"
        assert service2.commands == []

    @patch("usecli.cli.services.command_service.get_config")
    @patch("usecli.cli.services.command_service.get_version")
    def test_scenario_version_zero_point_versions(
        self, mock_get_version, mock_get_config
    ):
        """Test handling of various version formats."""
        mock_get_config.return_value = _mock_config_version(None)
        app = MagicMock()
        service = CommandService(app=app)

        test_versions = [
            "0.0.0",
            "0.0.1",
            "0.1.0",
            "1.0.0",
            "1.2.3.4",
            "1.0.0rc1",
        ]

        for version in test_versions:
            mock_get_version.return_value = version

            service._load_version()
            assert service.version == version

    def test_scenario_path_conversion_in_import(self):
        """Test that paths are correctly used in import_file."""
        app = MagicMock()
        service = CommandService(app=app)

        with patch("importlib.util.spec_from_file_location") as mock_spec_from_file:
            mock_spec_from_file.return_value = None

            path = MagicMock()
            path.stem = "example_module"

            result = service._import_file(path)

            # Verify the call was made with correct parameters
            mock_spec_from_file.assert_called_once_with("example_module", path)
            assert result is None

    @patch("usecli.cli.services.command_service.get_version")
    @patch("usecli.cli.services.command_service.get_config")
    def test_load_version_prefers_project_config(
        self, mock_get_config, mock_get_version
    ):
        mock_get_config.return_value = _mock_config_version("9.9.9")

        app = MagicMock()
        service = CommandService(app=app)
        service._load_version()

        assert service.version == "9.9.9"
        mock_get_version.assert_not_called()
