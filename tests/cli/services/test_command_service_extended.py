"""Tests for usecli.cli.services.command_service — CommandService."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from usecli.cli.services.command_service import (
    CommandService,
    _is_package_not_found,
    get_version,
)


class TestGetVersion:
    @patch("importlib.metadata.version")
    def test_returns_version(self, mock_version):
        mock_version.return_value = "1.2.3"
        assert get_version("usecli") == "1.2.3"


class TestIsPackageNotFound:
    def test_returns_true_for_package_not_found(self):
        from importlib.metadata import PackageNotFoundError

        err = PackageNotFoundError("pkg")
        assert _is_package_not_found(err) is True

    def test_returns_false_for_other_errors(self):
        assert _is_package_not_found(ValueError("test")) is False

    def test_returns_false_for_os_error(self):
        assert _is_package_not_found(OSError("test")) is False


class TestCommandService:
    def _make_service(self):
        app = MagicMock()
        return CommandService(app)

    def test_init(self):
        service = self._make_service()
        assert service.commands == []
        assert service.version == "0.0.0"
        assert service._skip_usecli_only_commands is False

    @patch("usecli.cli.services.command_service.get_version")
    @patch("usecli.cli.services.command_service.get_config")
    def test_load_version_from_usecli_package(self, mock_config, mock_get_ver):
        mock_config.return_value = MagicMock(
            get_project_version=MagicMock(return_value=None),
        )
        mock_get_ver.return_value = "2.0.0"

        service = self._make_service()
        with patch.object(service, "_get_application_version", return_value=None):
            service._load_version()
        assert service.version == "2.0.0"

    @patch("usecli.cli.services.command_service.get_config")
    def test_load_version_from_config(self, mock_config):
        mock_config.return_value = MagicMock(
            get_project_version=MagicMock(return_value="1.5.0"),
        )

        service = self._make_service()
        with patch.object(service, "_get_application_version", return_value=None):
            service._load_version()
        assert service.version == "1.5.0"

    @patch("usecli.cli.services.command_service.get_version")
    @patch("usecli.cli.services.command_service.get_config")
    def test_load_version_fallback_to_zero(self, mock_config, mock_get_ver):
        from importlib.metadata import PackageNotFoundError

        mock_config.return_value = MagicMock(
            get_project_version=MagicMock(return_value=None),
        )
        mock_get_ver.side_effect = PackageNotFoundError("usecli")

        service = self._make_service()
        with patch.object(service, "_get_application_version", return_value=None):
            service._load_version()
        assert service.version == "0.0.0"

    @patch("usecli.cli.services.command_service.get_config")
    def test_load_version_from_application_distribution(self, mock_config):
        mock_config.return_value = MagicMock()
        service = self._make_service()
        with patch.object(service, "_get_application_version", return_value="3.0.0"):
            service._load_version()
        assert service.version == "3.0.0"

    def test_load_from_dir_nonexistent(self, tmp_path):
        service = self._make_service()
        service._load_from_dir(tmp_path / "nonexistent")
        # Should not raise
        assert service.commands == []

    def test_load_from_dir_skips_init(self, tmp_path):
        (tmp_path / "__init__.py").write_text("")
        service = self._make_service()
        service._load_from_dir(tmp_path)
        # __init__.py should be skipped
        assert service.commands == []

    def test_load_from_dir_skips_internal(self, tmp_path):
        internal_dir = tmp_path / "internal"
        internal_dir.mkdir()
        (internal_dir / "hidden.py").write_text("class Hidden: pass")
        service = self._make_service()
        service._load_from_dir(tmp_path)
        # internal directory should be skipped
        assert service.commands == []

    def test_load_from_dir_skips_usecli_only_commands(self, tmp_path):
        (tmp_path / "init_command.py").write_text("class Cmd: pass")
        service = self._make_service()
        service._skip_usecli_only_commands = True
        service._load_from_dir(tmp_path)
        assert service.commands == []

    def test_load_from_dir_skips_make_dir(self, tmp_path):
        make_dir = tmp_path / "make"
        make_dir.mkdir()
        (make_dir / "cmd.py").write_text("class Cmd: pass")
        service = self._make_service()
        service._skip_usecli_only_commands = True
        service._load_from_dir(tmp_path)
        assert service.commands == []
