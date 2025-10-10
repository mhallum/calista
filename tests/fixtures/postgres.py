"""PostgreSQL related fixtures for CALISTA.

PostgreSQL engines are backed by a temporary Postgres 17 instance launched with
Testcontainers and migrated to Alembic head.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import TYPE_CHECKING

import docker
import pytest
from alembic import command
from sqlalchemy import text

from calista import config
from calista.adapters.db.engine import make_engine

try:
    from testcontainers.postgres import (
        PostgresContainer,  # pyright: ignore[reportMissingTypeStubs]
    )
except Exception:  # pragma: no cover # pylint: disable=broad-except
    PostgresContainer = (  # pylint: disable=invalid-name
        None  # will skip if not installed
    )

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

## adjust pylint to deal with fixtures
# pylint: disable=redefined-outer-name


# --- Auto-skip Docker/Testcontainers-backed tests when Docker daemon is unavailable ---


def _docker_available() -> bool:
    try:
        docker.from_env().ping()
    except Exception:  # pylint: disable=broad-except
        return False
    return True


DOCKER_UP = _docker_available()


def pytest_collection_modifyitems(items):
    """Skip Postgres/Testcontainers tests if Docker is unavailable."""
    # pylint: disable=magic-value-comparison
    if DOCKER_UP:
        return
    skip = pytest.mark.skip(reason="Docker/Testcontainers backend not available")
    for item in items:
        if "postgres_engine" in getattr(item, "fixturenames", ()):
            item.add_marker(skip)
        elif "pg_url" in getattr(item, "fixturenames", ()):
            item.add_marker(skip)
        elif "pg_url_base" in getattr(item, "fixturenames", ()):
            item.add_marker(skip)
        elif "testcontainers" in item.nodeid or "postgres" in item.nodeid:
            item.add_marker(skip)


# --- Engines ------------------------------------------------------------------


@pytest.fixture
def pg_url_base() -> Iterator[str]:
    """Session Postgres 17 container URL, unmigrated.

    Spawns a Testcontainers `postgres:17` instance and yields its connection URL
    for the remainder of the test session. The container is torn down automatically.

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
        yield url


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
        command.upgrade(config.build_alembic_config(url), "head")
        yield url


@pytest.fixture
def postgres_engine(pg_url: str) -> Iterator[Engine]:
    """Per-test Postgres engine bound to the session container.

    Ensures the database is at Alembic head (idempotent), yields an Engine
    built via `make_engine()`, then cleans up by truncating `event_store`
    (resetting sequences) and disposing the engine.

    Yields:
        Engine: SQLAlchemy engine connected to the session's Postgres.
    """
    command.upgrade(config.build_alembic_config(pg_url), "head")
    eng = make_engine(pg_url)
    try:
        yield eng
    finally:
        # clean between tests that used this engine
        with eng.begin() as conn:
            conn.execute(text("TRUNCATE TABLE event_store RESTART IDENTITY CASCADE"))
        eng.dispose()
