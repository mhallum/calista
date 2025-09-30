"""Unit tests for calista.adapters.redactor.Redactor.

These tests verify that sensitive information (passwords, tokens, API keys,
etc.) is redacted correctly from database URLs and plain strings. Each test
case provides an input string and the expected outputs for non-strict and
strict sanitization modes.
"""

import pytest

from calista.adapters.redactor import Redactor
from calista.interfaces.redactor import RedactorMode

cases = [
    (
        "postgresql://alice:abc123@host/db",
        "postgresql://alice:***@host/db",
        "postgresql://***:***@host/db",
    ),
    (
        "mysql+pymysql://alice:pass@localhost:3306/mydb",
        "mysql+pymysql://alice:***@localhost:3306/mydb",
        "mysql+pymysql://***:***@localhost:3306/mydb",
    ),
    (
        "sqlite:///absolute/path/to/file.db",
        "sqlite:///absolute/path/to/file.db",
        "sqlite:///absolute/path/to/file.db",
    ),
    (
        "postgresql://host/db?password=abc123&sslmode=require",
        "postgresql://host/db?password=***&sslmode=require",
        "postgresql://host/db?password=***&sslmode=require",
    ),
    (
        "postgresql://host/db?user=foo&token=abc",
        "postgresql://host/db?user=foo&token=***",
        "postgresql://host/db?user=***&token=***",
    ),
    (
        "postgresql://host/db?apikey=xyz&connect_timeout=10",
        "postgresql://host/db?apikey=***&connect_timeout=10",
        "postgresql://host/db?apikey=***&connect_timeout=10",
    ),
    (
        "mysql://alice:abc123@host/db?access_token=abcd1234",
        "mysql://alice:***@host/db?access_token=***",
        "mysql://***:***@host/db?access_token=***",
    ),
    (
        "postgresql://host/db?PaSsWoRd=secret",
        "postgresql://host/db?PaSsWoRd=***",
        "postgresql://host/db?PaSsWoRd=***",
    ),
    (
        "postgresql://host/db?api-key=xyz",
        "postgresql://host/db?api-key=***",
        "postgresql://host/db?api-key=***",
    ),
    (
        "Server=myServer;Database=myDB;Uid=alice;Pwd=myPass;",
        "Server=myServer;Database=myDB;Uid=alice;Pwd=***",
        "Server=myServer;Database=myDB;Uid=***;Pwd=***",
    ),
    (
        "Driver={SQL Server};Server=serverName;Database=myDB;Uid=Bob;Pwd=myPass;",
        "Driver={SQL Server};Server=serverName;Database=myDB;Uid=Bob;Pwd=***",
        "Driver={SQL Server};Server=serverName;Database=myDB;Uid=***;Pwd=***",
    ),
    ("password: abc", "password: ***", "password: ***"),
    ("pwd: 12345", "pwd: ***", "pwd: ***"),
    ("token: xyz123", "token: ***", "token: ***"),
    ("api_key: abc123", "api_key: ***", "api_key: ***"),
    (
        "password: abc token: def api_key: ghi username: alice",
        "password: *** token: *** api_key: *** username: alice",
        "password: *** token: *** api_key: *** username: ***",
    ),
    (
        "secret: foo passwd: bar pwd: baz uid: alice123",
        "secret: *** passwd: *** pwd: *** uid: alice123",
        "secret: *** passwd: *** pwd: *** uid: ***",
    ),
    ("not a url", "not a url", "not a url"),
    (
        "postgresql://alice:@host/db",
        "postgresql://alice:@host/db",
        "postgresql://***:@host/db",
    ),
    (
        "http://example.com?authorization=Bearer X.Y.Z",
        "http://example.com?authorization=***",
        "http://example.com?authorization=***",
    ),
    ("bareword", "bareword", "bareword"),
]


@pytest.mark.parametrize(
    "case",
    cases,
    ids=[c[0] for c in cases],
)
def test_safe_db_url(case):
    """Verify safe_db_url redacts sensitive information.

    Each parametrized `case` is a tuple of:
        (input_string, expected_non_strict, expected_strict)

    The test asserts that safe_db_url produces the expected redacted string
    when called with strict=False and strict=True.
    """
    input_url, expected_non_strict, expected_strict = case

    non_strict_redactor = Redactor(mode=RedactorMode.LENIENT)
    non_strict_result = non_strict_redactor.sanitize_db_url(input_url)
    non_strict_msg = (
        "\nExpected\n    "
        f"{expected_non_strict}\n"
        "but got\n    "
        f"{non_strict_result}\n"
        "for input\n    "
        f"{input_url}"
    )
    assert non_strict_result == expected_non_strict, non_strict_msg

    strict_redactor = Redactor(mode=RedactorMode.STRICT)
    strict_result = strict_redactor.sanitize_db_url(input_url)
    strict_msg = (
        "\nExpected\n    "
        f"{expected_strict}\n"
        "but got\n    "
        f"{strict_result}\n"
        "for input\n    "
        f"{input_url}"
    )
    assert strict_result == expected_strict, strict_msg


def test_redactor_mode_property():
    """Verify that Redactor.mode property returns the correct mode."""
    lenient_redactor = Redactor(mode=RedactorMode.LENIENT)
    assert lenient_redactor.mode == RedactorMode.LENIENT

    strict_redactor = Redactor(mode=RedactorMode.STRICT)
    assert strict_redactor.mode == RedactorMode.STRICT
