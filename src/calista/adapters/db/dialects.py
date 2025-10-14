"""Utility enums and helpers for database dialect handling.

This module defines the set of supported database dialect names used by
CALISTA. Centralizing these names as an Enum avoids scattering string
literals (e.g., "postgresql", "sqlite") throughout the codebase and makes
dialect checks type-safe and less error-prone.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine


class UnsupportedDialect(Exception):
    """Raised when an unsupported database dialect is encountered."""


class DialectName(str, Enum):
    """Enumeration of supported SQLAlchemy dialect names.

    Used to normalize and check the database backend in a type-safe way,
    instead of relying on raw string literals.

    Attributes:
        POSTGRES: PostgreSQL dialect (``"postgresql"``).
        SQLITE:   SQLite dialect (``"sqlite"``).
    """

    POSTGRES = "postgresql"
    SQLITE = "sqlite"

    @classmethod
    def from_string(cls, dialect_str: str) -> DialectName:
        """Normalize and convert an arbitrary dialect string to DialectName.

        Accepts common aliases and driver-qualified names (e.g., 'postgres',
        'postgresql+psycopg', 'sqlite', 'sqlite+pysqlite').

        Args:
            dialect_str: a raw dialect string

        Returns:
            The corresponding DialectName enum member.

        Raises:
            UnsupportedDialect: if the dialect is not recognized or supported.
        """

        raw = (dialect_str or "").strip().lower()
        # Strip driver suffix if present
        base = raw.split("+", 1)[0]

        # Map common aliases
        if base in {"postgres", "postgresql", "pg"}:
            return cls.POSTGRES
        if base in {"sqlite"}:
            return cls.SQLITE

        raise UnsupportedDialect(f"Unsupported dialect: {dialect_str!r}")

    @classmethod
    def from_sqlalchemy(cls, obj: Engine | Connection) -> "DialectName":
        """Extract dialect from a SQLAlchemy Engine or Connection.

        Args:
            obj: SQLAlchemy Engine or Connection instance.

        Returns:
            The corresponding DialectName enum member.

        Raises:
            UnsupportedDialect: if the dialect is not recognized or supported.
        """
        try:
            name = obj.dialect.name
        except AttributeError as e:
            raise UnsupportedDialect(
                f"Object {type(obj).__name__} does not expose .dialect.name"
            ) from e
        return cls.from_string(name)
