"""Comprehensive tests for path validators."""

import os

import pytest

from usecli.cli.core.exceptions import UsecliBadParameter
from usecli.cli.core.validators.path import (
    validate_directory_exists,
    validate_file_exists,
    validate_path_exists,
)


class TestValidatePathExists:
    """Test suite for validate_path_exists validator."""

    def test_existing_file_path(self, tmp_path):
        """Test that existing file path passes validation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = validate_path_exists(str(test_file))
        assert result == str(test_file)

    def test_existing_directory_path(self, tmp_path):
        """Test that existing directory path passes validation."""
        result = validate_path_exists(str(tmp_path))
        assert result == str(tmp_path)

    def test_nonexistent_path(self, tmp_path):
        """Test that nonexistent path raises UsecliBadParameter."""
        nonexistent = str(tmp_path / "nonexistent" / "path.txt")

        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_path_exists(nonexistent)

        assert "Path does not exist" in str(exc_info.value)
        assert nonexistent in str(exc_info.value)
        assert exc_info.value.param_hint == "--path"

    def test_empty_path_string(self, tmp_path):
        """Test that empty path string raises UsecliBadParameter."""
        with pytest.raises(UsecliBadParameter):
            validate_path_exists("")

    def test_relative_existing_path(self, tmp_path):
        """Test that relative existing paths work."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # Change to tmp directory and use relative path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = validate_path_exists("test.txt")
            assert result == "test.txt"
        finally:
            os.chdir(original_cwd)

    def test_hidden_file_path(self, tmp_path):
        """Test that hidden file paths are validated correctly."""
        hidden_file = tmp_path / ".hidden"
        hidden_file.write_text("content")

        result = validate_path_exists(str(hidden_file))
        assert result == str(hidden_file)


class TestValidateFileExists:
    """Test suite for validate_file_exists validator."""

    def test_existing_file(self, tmp_path):
        """Test that existing file passes validation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result = validate_file_exists(str(test_file))
        assert result == str(test_file)

    def test_nonexistent_file(self, tmp_path):
        """Test that nonexistent file raises UsecliBadParameter."""
        nonexistent = str(tmp_path / "nonexistent.txt")

        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_file_exists(nonexistent)

        assert "File does not exist" in str(exc_info.value)
        assert nonexistent in str(exc_info.value)
        assert exc_info.value.param_hint == "--file"

    def test_directory_instead_of_file(self, tmp_path):
        """Test that directory is rejected when file is expected."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_file_exists(str(tmp_path))

        assert "Path is not a file" in str(exc_info.value)
        assert exc_info.value.param_hint == "--file"

    def test_file_with_various_extensions(self, tmp_path):
        """Test that files with various extensions are validated correctly."""
        extensions = [".txt", ".json", ".py", ".md", ".pdf"]

        for ext in extensions:
            test_file = tmp_path / f"test{ext}"
            test_file.write_text("content")

            result = validate_file_exists(str(test_file))
            assert result == str(test_file)

    def test_empty_file(self, tmp_path):
        """Test that empty files are still validated as files."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        result = validate_file_exists(str(empty_file))
        assert result == str(empty_file)

    def test_large_file(self, tmp_path):
        """Test that large files are validated correctly."""
        large_file = tmp_path / "large.txt"
        large_file.write_text("x" * 1000000)  # 1MB of data

        result = validate_file_exists(str(large_file))
        assert result == str(large_file)

    def test_symlink_to_file(self, tmp_path):
        """Test that symlinks to files are validated as files."""
        original_file = tmp_path / "original.txt"
        original_file.write_text("content")

        symlink_file = tmp_path / "symlink.txt"
        symlink_file.symlink_to(original_file)

        result = validate_file_exists(str(symlink_file))
        assert result == str(symlink_file)

    def test_nested_file(self, tmp_path):
        """Test that nested files are validated correctly."""
        nested_dir = tmp_path / "nested" / "deep" / "structure"
        nested_dir.mkdir(parents=True, exist_ok=True)

        test_file = nested_dir / "file.txt"
        test_file.write_text("content")

        result = validate_file_exists(str(test_file))
        assert result == str(test_file)


class TestValidateDirectoryExists:
    """Test suite for validate_directory_exists validator."""

    def test_existing_directory(self, tmp_path):
        """Test that existing directory passes validation."""
        result = validate_directory_exists(str(tmp_path))
        assert result == str(tmp_path)

    def test_nonexistent_directory(self, tmp_path):
        """Test that nonexistent directory raises UsecliBadParameter."""
        nonexistent = str(tmp_path / "nonexistent" / "dir")

        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_directory_exists(nonexistent)

        assert "Directory does not exist" in str(exc_info.value)
        assert nonexistent in str(exc_info.value)
        assert exc_info.value.param_hint == "--dir"

    def test_file_instead_of_directory(self, tmp_path):
        """Test that file is rejected when directory is expected."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_directory_exists(str(test_file))

        assert "Path is not a directory" in str(exc_info.value)
        assert exc_info.value.param_hint == "--dir"

    def test_nested_directory(self, tmp_path):
        """Test that nested directories are validated correctly."""
        nested_dir = tmp_path / "level1" / "level2" / "level3"
        nested_dir.mkdir(parents=True, exist_ok=True)

        result = validate_directory_exists(str(nested_dir))
        assert result == str(nested_dir)

    def test_hidden_directory(self, tmp_path):
        """Test that hidden directories are validated correctly."""
        hidden_dir = tmp_path / ".hidden_dir"
        hidden_dir.mkdir()

        result = validate_directory_exists(str(hidden_dir))
        assert result == str(hidden_dir)

    def test_directory_with_special_chars(self, tmp_path):
        """Test that directories with special characters are validated."""
        special_dir = tmp_path / "dir-with_special.chars"
        special_dir.mkdir()

        result = validate_directory_exists(str(special_dir))
        assert result == str(special_dir)

    def test_empty_directory(self, tmp_path):
        """Test that empty directories are validated correctly."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = validate_directory_exists(str(empty_dir))
        assert result == str(empty_dir)

    def test_directory_with_files(self, tmp_path):
        """Test that directories containing files are validated correctly."""
        test_dir = tmp_path / "with_files"
        test_dir.mkdir()

        for i in range(5):
            (test_dir / f"file_{i}.txt").write_text(f"content {i}")

        result = validate_directory_exists(str(test_dir))
        assert result == str(test_dir)

    def test_symlink_to_directory(self, tmp_path):
        """Test that symlinks to directories are validated as directories."""
        original_dir = tmp_path / "original_dir"
        original_dir.mkdir()

        symlink_dir = tmp_path / "symlink_dir"
        symlink_dir.symlink_to(original_dir)

        result = validate_directory_exists(str(symlink_dir))
        assert result == str(symlink_dir)


class TestPathValidatorIntegration:
    """Integration tests for path validators."""

    def test_path_validators_with_same_location(self, tmp_path):
        """Test that different validators handle the same location appropriately."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # File validators should succeed
        assert validate_path_exists(str(test_file)) == str(test_file)
        assert validate_file_exists(str(test_file)) == str(test_file)

        # Directory validator should fail
        with pytest.raises(UsecliBadParameter):
            validate_directory_exists(str(test_file))

    def test_path_validators_with_directory(self, tmp_path):
        """Test that validators handle directories correctly."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        # Path validator should succeed
        assert validate_path_exists(str(test_dir)) == str(test_dir)

        # Directory validator should succeed
        assert validate_directory_exists(str(test_dir)) == str(test_dir)

        # File validator should fail
        with pytest.raises(UsecliBadParameter):
            validate_file_exists(str(test_dir))

    def test_multiple_validations_on_same_file(self, tmp_path):
        """Test that multiple validations can be performed on the same file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        result1 = validate_path_exists(str(test_file))
        result2 = validate_file_exists(str(test_file))

        assert result1 == str(test_file)
        assert result2 == str(test_file)
