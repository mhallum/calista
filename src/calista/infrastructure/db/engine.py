"""Database engine factory and helpers.

This module centralizes creation of SQLAlchemy Engines and applies
backend-specific tuning:

- **SQLite**: adds connection PRAGMAs to enforce foreign keys, enable WAL,
  and tune durability/temporary storage.
- **Other backends**: no tuning applied here (future PRs may add a UTC hook
  for Postgres).

Use this module whenever you need an Engine so that all connections are
consistently configured.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL, make_url

if TYPE_CHECKING:
    from sqlite3 import Connection as SQLiteConnection

    from sqlalchemy.engine import Engine

SQLITE_NAMES = {"sqlite", "sqlite+pysqlite"}


def is_sqlite(url: str | URL) -> bool:
    """Return True if the given SQLAlchemy URL or string corresponds to SQLite.

    Args:
        url: A database URL string or SQLAlchemy :class:`URL`.

    Returns:
        bool: True if the backend is SQLite, otherwise False.
    """
    u = make_url(str(url))
    return u.get_backend_name() in SQLITE_NAMES


def make_engine(url: str | URL, *, echo: bool = False) -> Engine:
    """Create a SQLAlchemy Engine for the given URL.

    If the backend is SQLite, applies a set of PRAGMAs to improve safety and
    concurrency for development/test usage:
        - ``foreign_keys=ON`` (enforce referential integrity)
        - ``journal_mode=WAL`` (write-ahead logging for concurrency)
        - ``synchronous=NORMAL`` (balanced durability)
        - ``temp_store=MEMORY`` (reduce temp file I/O)

    Args:
        url: Database connection URL (str or :class:`URL`).
        echo: If True, log SQL statements.

    Returns:
        Engine: Configured SQLAlchemy Engine.
    """

    engine = create_engine(url, echo=echo, future=True)

    if is_sqlite(url):

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn: SQLiteConnection, conn_record):  # type: ignore #pylint: disable=W0613
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON;")
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")
            cur.execute("PRAGMA temp_store=MEMORY;")
            cur.close()

    return engine
