"""Comprehensive tests for string validators."""

import pytest

from usecli.cli.core.exceptions import UsecliBadParameter
from usecli.cli.core.validators.string import validate_command_name, validate_not_empty


class TestValidateNotEmpty:
    """Test suite for validate_not_empty validator."""

    @pytest.mark.parametrize(
        "value",
        [
            "hello",
            "a",
            "test value",
            "123",
            "Test-Value_123",
            "hello world with spaces",
            "special!@#$%characters",
            "multiline\nstring",
        ],
    )
    def test_valid_non_empty_strings(self, value):
        """Test that non-empty strings pass validation."""
        result = validate_not_empty(value)
        assert result == value

    @pytest.mark.parametrize(
        "value,description",
        [
            ("", "empty string"),
            ("   ", "whitespace only"),
            ("\t", "tab only"),
            ("\n", "newline only"),
            ("\t\n  ", "mixed whitespace"),
            ("  \t  \n  ", "complex whitespace"),
        ],
    )
    def test_invalid_empty_strings(self, value, description):
        """Test that empty/whitespace strings raise UsecliBadParameter."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_not_empty(value)

        assert "Value cannot be empty" in str(exc_info.value)
        assert exc_info.value.param_hint == "value"

    def test_single_space(self):
        """Test that single space is considered empty."""
        with pytest.raises(UsecliBadParameter):
            validate_not_empty(" ")

    def test_string_with_leading_trailing_whitespace(self):
        """Test that strings with leading/trailing whitespace but content pass."""
        result = validate_not_empty("  hello  ")
        assert result == "  hello  "

    def test_empty_string_error_message(self):
        """Test that empty string has correct error message."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_not_empty("")

        assert "Value cannot be empty" in str(exc_info.value)

    def test_whitespace_only_error_message(self):
        """Test that whitespace-only string has correct error message."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_not_empty("     ")

        assert "Value cannot be empty" in str(exc_info.value)

    @pytest.mark.parametrize(
        "value",
        [
            "0",
            "False",
            "None",
            "null",
        ],
    )
    def test_falsy_looking_strings_are_valid(self, value):
        """Test that strings that look like falsy values are still valid."""
        result = validate_not_empty(value)
        assert result == value


class TestValidateCommandName:
    """Test suite for validate_command_name validator."""

    @pytest.mark.parametrize(
        "name",
        [
            "test",
            "test_command",
            "test-command",
            "test_command_123",
            "test-command-123",
            "_private",
            "_",
            "a",
            "A",
            "MyCommand",
            "my-command",
            "my_command",
            "cmd123",
            "CMD",
            "_test_",
            "_test-cmd",
        ],
    )
    def test_valid_command_names(self, name):
        """Test that valid command names pass validation."""
        result = validate_command_name(name)
        assert result == name

    @pytest.mark.parametrize(
        "name,expected_error",
        [
            ("", "Command name cannot be empty"),
            ("123", "Invalid command name"),
            ("1test", "Invalid command name"),
            ("9_cmd", "Invalid command name"),
            ("test command", "Invalid command name"),
            ("test@command", "Invalid command name"),
            ("test.command", "Invalid command name"),
            ("test/command", "Invalid command name"),
            ("test\\command", "Invalid command name"),
            ("test:command", "Invalid command name"),
            ("test;command", "Invalid command name"),
            ("test|command", "Invalid command name"),
            ("-test", "Invalid command name"),
            ("123-cmd", "Invalid command name"),
        ],
    )
    def test_invalid_command_names(self, name, expected_error):
        """Test that invalid command names raise UsecliBadParameter."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_command_name(name)

        assert expected_error in str(exc_info.value)
        assert exc_info.value.param_hint == "NAME"

    def test_command_name_empty_string(self):
        """Test that empty string raises appropriate error."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_command_name("")

        assert "Command name cannot be empty" in str(exc_info.value)

    def test_command_name_starting_with_digit_rejected(self):
        """Test that command names starting with digits are rejected."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_command_name("1test")

        assert "Invalid command name" in str(exc_info.value)

    def test_command_name_starting_with_special_char_rejected(self):
        """Test that command names starting with special chars are rejected."""
        invalid_starts = ["-", ".", "@", "#", "$", "%"]

        for char in invalid_starts:
            with pytest.raises(UsecliBadParameter):
                validate_command_name(f"{char}test")

    def test_command_name_with_hyphens(self):
        """Test that command names can use hyphens."""
        valid_names = ["test-cmd", "my-command", "do-something-great"]

        for name in valid_names:
            result = validate_command_name(name)
            assert result == name

    def test_command_name_with_underscores(self):
        """Test that command names can use underscores."""
        valid_names = ["test_cmd", "my_command", "do_something_great"]

        for name in valid_names:
            result = validate_command_name(name)
            assert result == name

    def test_command_name_with_numbers(self):
        """Test that command names can use numbers (not at start)."""
        valid_names = ["test1", "cmd2test", "command123"]

        for name in valid_names:
            result = validate_command_name(name)
            assert result == name

    def test_command_name_with_spaces_rejected(self):
        """Test that command names with spaces are rejected."""
        with pytest.raises(UsecliBadParameter):
            validate_command_name("test command")

    def test_command_name_with_mixed_valid_chars(self):
        """Test command names with mixed underscores, hyphens, and numbers."""
        valid_names = [
            "test_cmd-1",
            "my-command_v2",
            "_private_cmd",
            "cmd_1-a",
        ]

        for name in valid_names:
            result = validate_command_name(name)
            assert result == name

    @pytest.mark.parametrize(
        "name",
        [
            "test@cmd",
            "cmd#1",
            "test$command",
            "cmd%test",
            "test&cmd",
            "cmd*test",
            "test(cmd)",
            "cmd[test]",
            "test{cmd}",
            "cmd<test>",
            "test|cmd",
            "cmd\\test",
            "test/cmd",
            "cmd?test",
            "test!cmd",
            "cmd~test",
            "test`cmd",
            "cmd'test",
            'test"cmd',
            "cmd+test",
            "test=cmd",
        ],
    )
    def test_command_name_special_chars_rejected(self, name):
        """Test that command names with special characters are rejected."""
        with pytest.raises(UsecliBadParameter):
            validate_command_name(name)

    def test_command_name_case_sensitive(self):
        """Test that command name validation is case sensitive."""
        # Both uppercase and lowercase versions should be valid
        assert validate_command_name("test") == "test"
        assert validate_command_name("TEST") == "TEST"
        assert validate_command_name("Test") == "Test"
        assert validate_command_name("TeSt") == "TeSt"

    def test_command_name_long_name(self):
        """Test that long command names are validated."""
        long_name = "a" * 100
        result = validate_command_name(long_name)
        assert result == long_name

    def test_command_name_single_underscore(self):
        """Test that single underscore is valid."""
        result = validate_command_name("_")
        assert result == "_"

    def test_command_name_single_letter(self):
        """Test that single letters are valid."""
        for letter in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ":
            result = validate_command_name(letter)
            assert result == letter


class TestStringValidatorIntegration:
    """Integration tests for string validators."""

    def test_command_name_passes_not_empty(self):
        """Test that all valid command names are also valid non-empty strings."""
        valid_commands = ["test", "my_command", "my-command", "_private"]

        for cmd in valid_commands:
            assert validate_not_empty(cmd) == cmd
            assert validate_command_name(cmd) == cmd

    def test_not_empty_more_permissive_than_command_name(self):
        """Test that not_empty is more permissive than command_name."""
        # These pass not_empty but fail command_name
        test_values = [
            "123",
            "test@domain.com",
            "hello world",
            "path/to/file",
            "-test",
        ]

        for value in test_values:
            # Should pass not_empty
            assert validate_not_empty(value) == value

            # Should fail command_name
            with pytest.raises(UsecliBadParameter):
                validate_command_name(value)
