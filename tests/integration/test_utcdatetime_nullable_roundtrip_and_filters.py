"""Unit-style integration tests for the custom UTCDateTime type with a nullable column.

We exercise three meaningful behaviors across both backends (SQLite + Postgres):
1) SQL NULL round-trips to Python None (no accidental coercion).
2) A real value with an offset is normalized to tz-aware UTC on read.
3) SQL NULL semantics are preserved for IS NULL / IS NOT NULL filtering.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest
import sqlalchemy as sa

from calista.infrastructure.db.sa_types import UTCDateTime

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

# Some setup raises duplicate-code warnings,
# but I like having some things spelled out for clarity.
# pylint: disable=duplicate-code

# adjust pylint for dealing with pytest fixtures
# pylint: disable=redefined-outer-name

# Run this module against both backends via the existing engine fixtures.
pytestmark = pytest.mark.parametrize(
    "engine",
    ["sqlite_engine_file", "postgres_engine"],
    indirect=True,
)


@pytest.fixture
def tmp_table(engine: Engine) -> Iterator[sa.Table]:
    """Create a temporary table with a nullable UTCDateTime column and seed two rows:
    - id=1 with NULL processed_at
    - id=2 with processed_at at 2024-01-01T05:00:00-07:00 (normalizes to 12:00:00Z)
    Table is dropped after the test.
    """
    md = sa.MetaData()
    t = sa.Table(
        "tmp_events_optional",
        md,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("processed_at", UTCDateTime(), nullable=True),
        prefixes=["TEMPORARY"],
    )
    md.create_all(engine)
    with engine.begin() as conn:
        conn.execute(
            sa.insert(t),
            [
                {"id": 1, "processed_at": None},
                {
                    "id": 2,
                    "processed_at": datetime(
                        2024, 1, 1, 5, 0, 0, tzinfo=timezone(timedelta(hours=-7))
                    ),
                },
            ],
        )
    yield t
    md.drop_all(engine)


def test_utcdatetime_roundtrip_none(engine: Engine, tmp_table: sa.Table):
    """Row with NULL should round-trip to Python None (no coercion)."""
    with engine.begin() as conn:
        got = conn.execute(
            sa.select(tmp_table.c.processed_at).where(tmp_table.c.id == 1)
        ).scalar_one()
        assert got is None


def test_utcdatetime_roundtrip_value(engine: Engine, tmp_table: sa.Table):
    """Row with a real timestamp should normalize to tz-aware UTC on read."""
    with engine.begin() as conn:
        example_record_id = 2
        got = conn.execute(
            sa.select(tmp_table.c.processed_at).where(
                tmp_table.c.id == example_record_id
            )
        ).scalar_one()
        assert got == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_utcdatetime_null_filtering(engine: Engine, tmp_table: sa.Table):
    """Verify SQL NULL semantics are preserved for IS NULL / IS NOT NULL filters."""
    with engine.begin() as conn:
        nulls = conn.execute(
            sa.select(sa.func.count())  # pylint: disable=not-callable
            .select_from(tmp_table)
            .where(tmp_table.c.processed_at.is_(None))
        ).scalar_one()
        not_nulls = conn.execute(
            sa.select(sa.func.count())  # pylint: disable=not-callable
            .select_from(tmp_table)
            .where(tmp_table.c.processed_at.is_not(None))
        ).scalar_one()
        assert nulls == 1
        assert not_nulls == 1
