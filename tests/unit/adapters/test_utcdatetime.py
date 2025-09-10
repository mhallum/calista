"""Unit tests for calista.infrastructure.db.sa_types.UTCDateTime.

These tests exercise the type decorator directly, without creating tables
or running against a real database engine. They verify:

- .python_type property reports datetime.
- process_bind_param correctly normalizes None, naive, and tz-aware datetimes.
- process_literal_param integrates with SQL compilation (SQLite + Postgres).
- process_result_value handles None, datetimes, and non-datetime fallbacks.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import dialect as PostgresDialect
from sqlalchemy.dialects.sqlite import dialect as SQLiteDialect

from calista.adapters.db.dialects import DialectName
from calista.adapters.db.sa_types import UTCDateTime

if TYPE_CHECKING:
    from sqlalchemy.engine.interfaces import Dialect

# --- Direct unit tests for the custom type (no DB required) ---


def test_utcdatetime_python_type():
    """UTCDateTime.python_type should be datetime."""
    assert UTCDateTime().python_type is datetime


@pytest.mark.parametrize(
    "dialect", [SQLiteDialect(), PostgresDialect()], ids=["sqlite", "postgres"]
)
def test_bind_none_returns_none(dialect: Dialect):
    """Binding None should return None for any dialect."""
    custom_sa_type = UTCDateTime()
    assert custom_sa_type.process_bind_param(None, dialect) is None


@pytest.mark.parametrize(
    "dialect", [SQLiteDialect(), PostgresDialect()], ids=["sqlite", "postgres"]
)
def test_bind_naive_normalizes_to_utc(dialect: Dialect):
    """Naive datetime should be normalized to UTC (tz-aware for PG, naive for SQLite)."""
    custom_sa_type = UTCDateTime()
    out = custom_sa_type.process_bind_param(datetime(2024, 1, 1, 12, 0, 0), dialect)
    # SQLite path binds naive UTC; PG binds aware UTC. Normalize for assertion:
    if dialect.name == DialectName.SQLITE.value:
        assert out.tzinfo is None and out == datetime(2024, 1, 1, 12, 0, 0)
    else:
        assert out.tzinfo is not None and out == datetime(
            2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc
        )


@pytest.mark.parametrize(
    "dialect", [SQLiteDialect(), PostgresDialect()], ids=["sqlite", "postgres"]
)
def test_bind_aware_normalizes_to_utc(dialect: Dialect):
    """Tz-aware datetime should normalize to UTC (tz-aware for PG, naive UTC for SQLite)."""
    custom_sa_type = UTCDateTime()
    aware = datetime(2024, 1, 1, 5, 0, 0, tzinfo=timezone(timedelta(hours=-7)))
    out = custom_sa_type.process_bind_param(aware, dialect)
    if dialect.name == DialectName.SQLITE.value:
        assert out.tzinfo is None and out == datetime(2024, 1, 1, 12, 0, 0)
    else:
        assert out.tzinfo is not None and out == datetime(
            2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc
        )


def _compile_sql(dialect: Dialect, dt: datetime) -> str:
    """Compile a literal SELECT of a UTCDateTime value into SQL for inspection."""
    expr = sa.literal(dt, type_=UTCDateTime())
    stmt = sa.select(expr.label("dt"))
    return str(stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True}))


def test_process_literal_param_sqlite_compile():
    """Literal compilation under SQLite should normalize to UTC wall time."""
    sql = _compile_sql(
        SQLiteDialect(),
        datetime(2024, 1, 1, 5, 0, 0, tzinfo=timezone(timedelta(hours=-7))),
    )
    # normalized wall time should appear as 12:00:00
    assert re.search(r"2024-01-01 12:00:00(\.\d+)?", sql)


def test_process_literal_param_postgres_compile():
    """Literal compilation under Postgres should include UTC time in the SQL."""
    sql = _compile_sql(
        PostgresDialect(), datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    )
    expected_sql_timestamp = "2024-01-01 12:00:00"
    assert expected_sql_timestamp in sql  # representation may include +00:00 or casts


def test_process_result_value_non_datetime_fallback():
    """Non-datetime values passed to process_result_value should be returned unchanged."""
    custom_sa_type = UTCDateTime()
    test_none_dt_value = "not-a-datetime"
    out = custom_sa_type.process_result_value(test_none_dt_value, SQLiteDialect())
    assert out == test_none_dt_value
