"""Global pytest fixtures for CALISTA tests.

These fixtures expose pre-configured SQLite Engines for use in tests.
They ensure consistent database setup via `make_engine` (so PRAGMAs
are applied) and proper teardown (`engine.dispose()`), preventing
unclosed connection warnings.

Scope:
    - Defined in the global ``conftest.py`` so they are automatically
      available to all tests in the repository.

Fixtures:
    - sqlite_engine_file: File-backed SQLite Engine bound to a temp file.
    - sqlite_engine_memory: In-memory SQLite Engine.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.engine import URL

from calista.infrastructure.db.engine import make_engine

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


@pytest.fixture
def sqlite_engine_file(tmp_path: Path) -> Iterator[Engine]:
    """Provide a file-backed SQLite engine bound to a temporary file.

    Uses `make_engine` so SQLite PRAGMAs are applied.
    The engine is disposed after the test to close all DBAPI connections.

    Args:
        tmp_path: Pytest-provided temporary directory.

    Yields:
        Engine: A SQLAlchemy engine pointing to a file-backed SQLite DB.
    """
    url = str(URL.create("sqlite+pysqlite", database=str(tmp_path / "test.db")))
    engine = make_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def sqlite_engine_memory() -> Iterator[Engine]:
    """Provide an in-memory SQLite engine.

    Uses `make_engine` so SQLite PRAGMAs are applied.
    The engine is disposed after the test to close all DBAPI connections.

    Yields:
        Engine: A SQLAlchemy engine bound to an in-memory SQLite DB.
    """
    url = "sqlite+pysqlite:///:memory:"
    engine = make_engine(url)
    yield engine
    engine.dispose()
