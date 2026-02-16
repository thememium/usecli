"""Comprehensive tests for numeric validators."""

import pytest

from usecli.cli.core.exceptions import UsecliBadParameter
from usecli.cli.core.validators.numeric import validate_positive_int


class TestValidatePositiveInt:
    """Test suite for validate_positive_int validator."""

    @pytest.mark.parametrize(
        "value",
        [
            "1",
            "10",
            "100",
            "999",
            "1000",
            "9999",
            "2147483647",  # Large positive int
            "42",
        ],
    )
    def test_valid_positive_integers(self, value):
        """Test that valid positive integers pass validation."""
        result = validate_positive_int(value)
        assert result == value

    @pytest.mark.parametrize(
        "value,expected_error",
        [
            ("0", "Value must be a positive integer"),
            ("-1", "Value must be a positive integer"),
            ("-100", "Value must be a positive integer"),
            ("-9999", "Value must be a positive integer"),
            ("abc", "Value must be an integer"),
            ("12.5", "Value must be an integer"),
            ("1.0", "Value must be an integer"),
            ("", "Value must be an integer"),
            ("1a", "Value must be an integer"),
            ("a1", "Value must be an integer"),
            ("10.99", "Value must be an integer"),
            ("one", "Value must be an integer"),
        ],
    )
    def test_invalid_positive_integers(self, value, expected_error):
        """Test that invalid values raise UsecliBadParameter."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_positive_int(value)

        assert expected_error in str(exc_info.value)
        assert exc_info.value.param_hint == "value"

    def test_zero_not_positive(self):
        """Test that zero is rejected as not positive."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_positive_int("0")

        assert "Value must be a positive integer" in str(exc_info.value)

    def test_negative_integers_rejected(self):
        """Test that negative integers are rejected."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_positive_int("-42")

        assert "Value must be a positive integer" in str(exc_info.value)

    def test_float_strings_rejected(self):
        """Test that float strings are rejected."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_positive_int("3.14")

        assert "Value must be an integer" in str(exc_info.value)

    def test_non_numeric_strings_rejected(self):
        """Test that non-numeric strings are rejected."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_positive_int("hello")

        assert "Value must be an integer" in str(exc_info.value)

    def test_boundary_value_one(self):
        """Test that 1 is the minimum valid positive integer."""
        assert validate_positive_int("1") == "1"

    def test_large_positive_integers(self):
        """Test that large positive integers are accepted."""
        large_value = "999999999999"
        result = validate_positive_int(large_value)
        assert result == large_value

    @pytest.mark.parametrize(
        "value",
        [
            "1e10",  # Scientific notation
            "1E5",  # Scientific notation
        ],
    )
    def test_special_numeric_formats_rejected(self, value):
        """Test that scientific notation is rejected."""
        # Scientific notation should be rejected as it's not a plain integer
        with pytest.raises(UsecliBadParameter):
            validate_positive_int(value)

    @pytest.mark.parametrize(
        "value",
        [
            "+42",  # Plus sign (Python int() accepts this)
            " 42 ",  # Spaces (Python int() accepts this)
        ],
    )
    def test_special_numeric_formats_accepted(self, value):
        """Test that int() accepted formats work."""
        # Python's int() accepts these, so they pass validation
        result = validate_positive_int(value)
        assert result == value
