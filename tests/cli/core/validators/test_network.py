"""Comprehensive tests for network validators (email, URL, port)."""

import pytest

from usecli.cli.core.exceptions import UsecliBadParameter
from usecli.cli.core.validators.network import (validate_email, validate_port,
                                                validate_url)


class TestValidateEmail:
    """Test suite for validate_email validator."""

    @pytest.mark.parametrize(
        "email",
        [
            "user@example.com",
            "test.user@example.com",
            "user+tag@example.co.uk",
            "user_name@subdomain.example.com",
            "test123@test-domain.com",
            "a@b.co",
            "user.name+tag@example.museum",
        ],
    )
    def test_valid_emails(self, email):
        """Test that valid email addresses pass validation."""
        result = validate_email(email)
        assert result == email

    @pytest.mark.parametrize(
        "email,expected_error",
        [
            ("", "Email cannot be empty"),
            ("plainaddress", "Invalid email format"),
            ("user@", "Invalid email format"),
            ("user@domain", "Invalid email format"),
            ("user@domain.", "Invalid email format"),
            ("@domain.com", "Invalid email format"),
            ("user name@domain.com", "Invalid email format"),
            ("user@domain .com", "Invalid email format"),
            ("user @domain.com", "Invalid email format"),
        ],
    )
    def test_invalid_emails(self, email, expected_error):
        """Test that invalid email addresses raise UsecliBadParameter."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_email(email)

        assert expected_error in str(exc_info.value)
        assert exc_info.value.param_hint == "--email"

    def test_email_empty_string(self):
        """Test that empty string raises appropriate error."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_email("")

        assert "Email cannot be empty" in str(exc_info.value)
        assert exc_info.value.param_hint == "--email"


class TestValidateUrl:
    """Test suite for validate_url validator."""

    @pytest.mark.parametrize(
        "url",
        [
            "http://example.com",
            "https://example.com",
            "ftp://example.com",
            "https://www.example.com",
            "https://subdomain.example.co.uk",
            "http://example.com/path",
            "https://example.com/path?query=value",
            "ftp://ftp.example.com/file.txt",
            "https://example.com:8080",
            "http://192.168.1.1",
            "https://example.com/path/to/resource",
        ],
    )
    def test_valid_urls(self, url):
        """Test that valid URLs pass validation."""
        result = validate_url(url)
        assert result == url

    @pytest.mark.parametrize(
        "url,expected_error",
        [
            ("", "URL cannot be empty"),
            ("not-a-url", "Invalid URL format"),
            ("example.com", "Invalid URL format"),
            ("http://", "Invalid URL format"),
            ("htp://example.com", "Invalid URL format"),
            ("http:///example.com", "Invalid URL format"),
            ("http://example com", "Invalid URL format"),
            ("file://path/to/file", "Invalid URL format"),
            ("example.com/path", "Invalid URL format"),
        ],
    )
    def test_invalid_urls(self, url, expected_error):
        """Test that invalid URLs raise UsecliBadParameter."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_url(url)

        assert expected_error in str(exc_info.value)
        assert exc_info.value.param_hint == "--url"

    def test_url_case_insensitive(self):
        """Test that URL validation is case insensitive for scheme."""
        result = validate_url("HTTP://EXAMPLE.COM")
        assert result == "HTTP://EXAMPLE.COM"

        result = validate_url("HTTPS://example.com")
        assert result == "HTTPS://example.com"

    def test_url_empty_string(self):
        """Test that empty string raises appropriate error."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_url("")

        assert "URL cannot be empty" in str(exc_info.value)
        assert exc_info.value.param_hint == "--url"


class TestValidatePort:
    """Test suite for validate_port validator."""

    @pytest.mark.parametrize(
        "port",
        [
            "1",
            "22",
            "80",
            "443",
            "8080",
            "8000",
            "65535",
            "3000",
            "5432",
            "9000",
        ],
    )
    def test_valid_ports(self, port):
        """Test that valid port numbers pass validation."""
        result = validate_port(port)
        assert result == port

    @pytest.mark.parametrize(
        "port,expected_error",
        [
            ("0", "Port must be between 1 and 65535"),
            ("-1", "Port must be between 1 and 65535"),
            ("65536", "Port must be between 1 and 65535"),
            ("70000", "Port must be between 1 and 65535"),
            ("abc", "Port must be a valid integer"),
            ("12.5", "Port must be a valid integer"),
            ("", "Port must be a valid integer"),
            ("port", "Port must be a valid integer"),
            ("8080a", "Port must be a valid integer"),
        ],
    )
    def test_invalid_ports(self, port, expected_error):
        """Test that invalid port numbers raise UsecliBadParameter."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_port(port)

        assert expected_error in str(exc_info.value)
        assert exc_info.value.param_hint == "--port"

    def test_port_boundary_values(self):
        """Test port boundary values."""
        # Valid minimum
        assert validate_port("1") == "1"

        # Valid maximum
        assert validate_port("65535") == "65535"

        # Invalid below minimum
        with pytest.raises(UsecliBadParameter):
            validate_port("0")

        # Invalid above maximum
        with pytest.raises(UsecliBadParameter):
            validate_port("65536")

    def test_port_non_numeric(self):
        """Test that non-numeric ports are rejected."""
        with pytest.raises(UsecliBadParameter) as exc_info:
            validate_port("not-a-number")

        assert "Port must be a valid integer" in str(exc_info.value)

    def test_port_float(self):
        """Test that float ports are rejected."""
        with pytest.raises(UsecliBadParameter):
            validate_port("8080.5")
