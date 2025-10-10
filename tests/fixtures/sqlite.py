"""sqlite-specific fixtures"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from alembic import command
from sqlalchemy.engine import URL

from calista import config
from calista.adapters.db.engine import make_engine
from calista.adapters.db.metadata import metadata

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


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


@pytest.fixture
def sqlite_engine_file(tmp_path: Path) -> Iterator[Engine]:
    """File-backed SQLite engine migrated via Alembic (per test).

    For SQLite we prefer a temp *file* (not :memory:) so Alembic's schema
    changes persist across connections. This fixture:
      - builds a sqlite+pysqlite URL under the test's temp dir,
      - runs `alembic upgrade head` for that URL,
      - returns an Engine from `make_engine()` (so PRAGMAs apply),
      - disposes the engine at teardown.

    We do **not** downgrade on teardown—each test uses its own DB file.

    Yields:
        Engine: SQLAlchemy engine pointing at a temp file DB.
    """
    url = str(URL.create("sqlite+pysqlite", database=str(tmp_path / "test.db")))
    cfg = config.build_alembic_config(url)
    command.upgrade(cfg, "head")
    test_engine = make_engine(url)
    try:
        yield test_engine
    finally:
        test_engine.dispose()
