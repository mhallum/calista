"""Utility enums and helpers for database dialect handling.

This module defines the set of supported database dialect names used by
CALISTA. Centralizing these names as an Enum avoids scattering string
literals (e.g., "postgresql", "sqlite") throughout the codebase and makes
dialect checks type-safe and less error-prone.
"""

from __future__ import annotations

from enum import Enum


class DialectName(str, Enum):
    """Enumeration of supported SQLAlchemy dialect names.

    Used to normalize and check the database backend in a type-safe way,
    instead of relying on raw string literals.

    Attributes:
        POSTGRES: PostgreSQL dialect (``"postgresql"``).
        SQLITE:   SQLite dialect (``"sqlite"``).

    Example:
        ```
        >>> from sqlalchemy import create_engine
        >>> from calista.adapters.db.dialects import DialectName
        >>> engine = create_engine("postgresql+psycopg://user:pass@host/db")
        >>> DialectName(engine.dialect.name) is DialectName.POSTGRES
        True
        ```
    """

    POSTGRES = "postgresql"
    SQLITE = "sqlite"
