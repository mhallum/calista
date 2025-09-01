"""Global pytest fixtures for CALISTA tests.

These fixtures expose pre-configured SQLite and Postgres Engines for use in tests.
They ensure consistent database setup via `make_engine` (so SQLite PRAGMAs are
applied) and proper teardown (`engine.dispose()`), preventing unclosed connection
warnings.

Scope:
    - Defined in the global ``conftest.py`` so they are automatically
      available to all tests in the repository.

Fixtures:
    - sqlite_engine_file: File-backed SQLite Engine bound to a temp file.
    - sqlite_engine_memory: In-memory SQLite Engine.
    - postgres_engine: Postgres Engine (skips if CALISTA_TEST_PG_URL is unset).
    - engine: Indirection layer to parametrize over the above engines.
    - make_event: Test event factory producing a valid event_store row dict.

   Helpers:
    - ulid_like: 26-char ULID-ish string (length/uniqueness sufficient for tests).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy.engine import URL

from calista.infrastructure.db.engine import make_engine
from calista.infrastructure.db.metadata import metadata

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

# --- Engines ------------------------------------------------------------------


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
    test_engine = make_engine(url)
    metadata.create_all(test_engine)
    yield test_engine
    metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def sqlite_engine_memory() -> Iterator[Engine]:
    """Provide an in-memory SQLite engine.

    Uses `make_engine` so SQLite PRAGMAs are applied.
    The engine is disposed after the test to close all DBAPI connections.

    Yields:
        Engine: A SQLAlchemy engine bound to an in-memory SQLite DB.
    """
    url = "sqlite+pysqlite:///:memory:"
    test_engine = make_engine(url)
    metadata.create_all(test_engine)
    yield test_engine
    metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def postgres_engine() -> Iterator[Engine]:
    """Provide a Postgres engine from CALISTA_TEST_PG_URL.

    Skips the test if CALISTA_TEST_PG_URL is not set. Uses `make_engine` to ensure
    consistent engine options. Tables are created/dropped via shared `metadata`.

    Env:
        CALISTA_TEST_PG_URL: e.g., postgresql+psycopg://user:pass@localhost:5432/db

    Yields:
        Engine: A SQLAlchemy engine connected to Postgres.
    """
    if not (url := os.environ.get("CALISTA_TEST_PG_URL")):
        pytest.skip(
            "Set CALISTA_TEST_PG_URL for Postgres tests, e.g. "
            "postgresql+psycopg://user:pass@localhost:5432/db"
        )
    test_engine = make_engine(url)
    metadata.create_all(test_engine)
    yield test_engine
    metadata.drop_all(test_engine)
    test_engine.dispose()


# Helper to route to an existing engine fixture by name
@pytest.fixture
def engine(request: pytest.FixtureRequest) -> Engine:
    """Resolve to another engine fixture by name.

    This indirection allows tests to parametrize over engines.
    """
    return request.getfixturevalue(request.param)


# --- Helpers ------------------------------------------------------------------


def ulid_like() -> str:
    """Return a 26-character ULID-ish string.

    Tests only validate length/uniqueness, not ULID lexicographic semantics.
    """
    return uuid.uuid4().hex[:26].ljust(26, "0")


@pytest.fixture
def make_event() -> Callable[..., dict[str, Any]]:
    """Factory fixture: produce a valid event_store row dict.

    Accepts keyword overrides to adjust any field; for example:
        make_event(stream_id="s-123", version=2, payload={"x": 1})
        make_event(recorded_at=<datetime>)  # only for tests that explicitly exercise bind logic

    Returns:
        Callable[..., dict[str, Any]]: A builder function that returns a row dict.
    """

    def _make_event(**overrides: dict[str, Any]) -> dict[str, Any]:
        base: dict[str, Any] = {
            "stream_id": "test-stream",
            "stream_type": "TestAggregate",
            "version": 1,
            "event_id": ulid_like(),
            "event_type": "TestEvent",
            "payload": {"kind": "TEST", "value": 42},
            "metadata": {"source": "pytest"},
        }
        base.update(overrides)
        return base

    return _make_event
