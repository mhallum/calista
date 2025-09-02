"""Global pytest fixtures for CALISTA.

This module provides ready-to-use SQLAlchemy engines for SQLite and PostgreSQL
plus small helpers for building valid `event_store` rows.

PostgreSQL engines are backed by a temporary Postgres 17 instance launched with
Testcontainers and **migrated to Alembic head** (migrations are the source of truth).
SQLite engines are ephemeral and use `metadata.create_all()` for narrow unit-style
tests where running Alembic isn’t necessary.

Why:
  - Keep schema creation consistent (PG via Alembic).
  - Keep tests isolated and deterministic (per-test TRUNCATE/teardown).
  - Apply CALISTA engine defaults (PRAGMAs, pool settings) via `make_engine()`.

Fixtures:
  - sqlite_engine_file: File-backed SQLite engine (temp file).
  - sqlite_engine_memory: In-memory SQLite engine.
  - pg_url: Session-scoped Postgres URL from a Testcontainers PG17 instance,
            already migrated to Alembic head.
  - postgres_engine: Per-test Postgres engine bound to `pg_url`; cleans `event_store`
                     after each test.
  - engine: Indirection layer so tests can parametrize over engine fixtures.
  - make_event: Factory returning a dict suitable for inserting into `event_store`.

Helpers:
  - ulid_like: Returns a 26-character ULID-ish string (length/uniqueness only).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL

from alembic import command
from alembic.config import Config
from calista.infrastructure.db.engine import make_engine
from calista.infrastructure.db.metadata import metadata

try:
    from testcontainers.postgres import PostgresContainer  # pyright: ignore[reportMissingTypeStubs]
except Exception:  # pragma: no cover # pylint: disable=broad-except
    PostgresContainer = (  # pylint: disable=invalid-name
        None  # will skip if not installed
    )

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

## adjust pylint to deal with fixtures
# pylint: disable=redefined-outer-name

# --- Engines ------------------------------------------------------------------


@pytest.fixture
def sqlite_engine_memory() -> Iterator[Engine]:
    """In-memory SQLite engine for unit-style tests.

    Uses `make_engine()` so SQLite PRAGMAs are applied.
    Creates/drops tables with `metadata.create_all()` / `drop_all()`.

    Note: No Alembic migrations are run here, so migration-defined features
    (e.g., triggers/constraints created in migrations) are NOT present.

    Yields:
        Engine: SQLAlchemy engine bound to an in-memory DB.
    """
    url = "sqlite+pysqlite:///:memory:"
    test_engine = make_engine(url)
    metadata.create_all(test_engine)
    yield test_engine
    metadata.drop_all(test_engine)
    test_engine.dispose()


def _alembic_cfg(url: str) -> Config:
    """Build an Alembic `Config` using the repo’s `alembic.ini`, overriding the URL.

    Args:
        url: Full SQLAlchemy URL to run migrations against.

    Returns:
        Config: Alembic configuration object.
    """

    root = Path(__file__).resolve().parents[1]  # repo root (parent of tests/)
    config_file = root / "alembic.ini"
    assert config_file.exists(), f"Missing {config_file}"
    cfg = Config(str(config_file))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


@pytest.fixture(scope="session")
def pg_url() -> Iterator[str]:
    """Session Postgres 17 container URL, migrated to Alembic head once.

    Spawns a Testcontainers `postgres:17` instance, normalizes its URL to use
    `psycopg` (v3), runs `alembic upgrade head`, and yields the URL for the
    remainder of the test session. The container is torn down automatically.

    Skips if Testcontainers is not available.
    """

    if PostgresContainer is None:
        pytest.skip("testcontainers not installed")

    with PostgresContainer(
        image="postgres:17",
        username="calista",
        password="abc123",
        dbname="calista",
    ) as pg:
        # testcontainers returns psycopg2 URLs by default; normalize to psycopg v3
        url = pg.get_connection_url()  # e.g., postgresql+psycopg2://...
        url = re.sub(r"\+psycopg2\b", "+psycopg", url)
        command.upgrade(_alembic_cfg(url), "head")
        yield url


@pytest.fixture
def postgres_engine(pg_url: str) -> Iterator[Engine]:
    """Per-test Postgres engine bound to the session container.

    Ensures the database is at Alembic head (idempotent), yields an Engine
    built via `make_engine()`, then cleans up by truncating `event_store`
    (resetting sequences) and disposing the engine.

    Yields:
        Engine: SQLAlchemy engine connected to the session’s Postgres.
    """
    command.upgrade(_alembic_cfg(pg_url), "head")
    eng = make_engine(pg_url)
    try:
        yield eng
    finally:
        # clean between tests that used this engine
        with eng.begin() as conn:
            conn.execute(text("TRUNCATE TABLE event_store RESTART IDENTITY CASCADE"))
        eng.dispose()


@pytest.fixture
def sqlite_engine_file(tmp_path: Path) -> Iterator[Engine]:
    """File-backed SQLite engine migrated via Alembic (per test).

    For SQLite we prefer a temp *file* (not :memory:) so Alembic's schema
    changes persist across connections. This fixture:
      - builds a sqlite+pysqlite URL under the test’s temp dir,
      - runs `alembic upgrade head` for that URL,
      - returns an Engine from `make_engine()` (so PRAGMAs apply),
      - disposes the engine at teardown.

    We do **not** downgrade on teardown—each test uses its own DB file.

    Yields:
        Engine: SQLAlchemy engine pointing at a temp file DB.
    """
    url = str(URL.create("sqlite+pysqlite", database=str(tmp_path / "test.db")))
    cfg = _alembic_cfg(url)
    command.upgrade(cfg, "head")
    test_engine = make_engine(url)
    try:
        yield test_engine
    finally:
        test_engine.dispose()


# Helper to route to an existing engine fixture by name
@pytest.fixture
def engine(request: pytest.FixtureRequest) -> Engine:
    """Indirection fixture to parametrize over engine-providing fixtures.

    Example:
        ```py
        @pytest.mark.parametrize("engine", ["postgres_engine", "sqlite_engine_file"], indirect=True)
        def test_something(engine): ...
        ```
    """
    return request.getfixturevalue(request.param)


# --- Helpers ------------------------------------------------------------------


def ulid_like() -> str:
    """Return a 26-character ULID-like string.

    Good enough for tests that assert length/uniqueness; not lexicographically sortable.
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
