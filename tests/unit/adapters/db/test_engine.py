"""Unit tests for the database engine helpers.

These tests cover:
- Detection of SQLite vs. non-SQLite URLs.
- Creation of a SQLite engine for a given URL.
- Application of SQLite PRAGMAs on connect.
"""

from typing import TYPE_CHECKING

from sqlalchemy.engine import make_url

from calista.adapters.db.engine import is_sqlite

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


def test_is_sqlite_true_for_sqlite_url():
    """is_sqlite() should return True for SQLite URLs."""
    assert is_sqlite("sqlite:///:memory:")
    assert is_sqlite(make_url("sqlite+pysqlite:///file.db"))


def test_is_sqlite_false_for_postgres_url():
    """is_sqlite() should return False for non-SQLite URLs (e.g., Postgres)."""
    assert not is_sqlite("postgresql://u:p@localhost/db")
    assert not is_sqlite(make_url("postgresql+psycopg://u:p@localhost/db"))


def test_make_engine_creates_sqlite(sqlite_engine_file: "Engine"):
    """make_engine() should create a working SQLite engine from a given URL."""
    engine = sqlite_engine_file  # engine is created in fixture using make_engine()
    assert engine.url.database is not None
    assert engine.url.database.endswith("test.db")


def test_sqlite_pragmas_applied(sqlite_engine_file: "Engine"):
    """SQLite engines created by make_engine() should apply expected PRAGMAs."""
    engine = sqlite_engine_file  # engine is created in fixture using make_engine()
    with engine.connect() as cxn:
        fk = cxn.exec_driver_sql("PRAGMA foreign_keys;").scalar()
        jm = cxn.exec_driver_sql("PRAGMA journal_mode;").scalar()
        sync = cxn.exec_driver_sql("PRAGMA synchronous;").scalar()
        tmp = cxn.exec_driver_sql("PRAGMA temp_store;").scalar()
    assert fk == 1
    assert jm is not None
    assert jm.lower() in {"wal", "memory"}
    assert sync in {1, 2}
    assert tmp in {1, 2}
