"""Unit tests for database dialect handling."""

import pytest

from calista.adapters.db.dialects import DialectName, UnsupportedDialect

# pylint: disable=too-few-public-methods


@pytest.mark.parametrize(
    "input_str,expected",
    [
        ("postgresql", DialectName.POSTGRES),
        ("postgres", DialectName.POSTGRES),
        ("pg", DialectName.POSTGRES),
        ("postgresql+psycopg", DialectName.POSTGRES),
        ("sqlite", DialectName.SQLITE),
        ("sqlite+pysqlite", DialectName.SQLITE),
    ],
)
def test_from_string_aliases(input_str, expected):
    """Test that various dialect string aliases map correctly to DialectName."""
    assert DialectName.from_string(input_str) is expected


@pytest.mark.parametrize("bad", [None, "", "  ", "mysql", "duckdb"])
def test_from_string_rejects_unsupported(bad):
    """Test that unsupported or invalid dialect strings raise UnsupportedDialect."""
    with pytest.raises(UnsupportedDialect):
        DialectName.from_string(bad)


def test_from_sqlalchemy_accepts_engine_like_objects():
    """Test that from_sqlalchemy accepts objects with .dialect.name attribute."""

    class FakeDialect:  # minimal stub; no SQLAlchemy import needed
        """A fake dialect with a name attribute."""

        name = "postgresql+psycopg"

    class FakeEngine:
        """A fake engine exposing a dialect attribute."""

        dialect = FakeDialect()

    assert DialectName.from_sqlalchemy(FakeEngine()) is DialectName.POSTGRES  # type: ignore[arg-type]


def test_from_sqlalchemy_raises_when_missing_attribute():
    """Test that from_sqlalchemy raises UnsupportedDialect when .dialect.name is missing."""

    class NotAnEngine:  # no .dialect.name
        """A class that does not have a dialect attribute."""

    with pytest.raises(UnsupportedDialect):
        DialectName.from_sqlalchemy(NotAnEngine())  # type: ignore[arg-type]
