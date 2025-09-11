"""Integration tests for CALISTA's event_store schema.

These tests validate:
- Core constraints and uniqueness (stream_id+version, event_id).
- ULID length and version >= 1 CHECKs.
- Monotonic identity behavior of global_seq.
- JSON payload/metadata round-trip.
- Timestamp semantics per ADR-0009 (recorded_at MUST be UTC, tz-aware).
- Cross-dialect behavior on SQLite and Postgres.

All tests run against both backends via the parametrized `engine` fixture.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

import pytest
from sqlalchemy import func, insert, inspect, select
from sqlalchemy.exc import IntegrityError

from calista.adapters.eventstore.schema import event_store
from tests.helpers.time_asserts import assert_strict_utc

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

# mypy: disable-error-code=no-untyped-def

# Run this module against both backends via engine fixtures from conftest.py
pytestmark = pytest.mark.parametrize(
    "engine",
    ["sqlite_engine_file", "postgres_engine", "sqlite_engine_memory"],
    indirect=True,
)  # pylint: disable=duplicate-code


def test_insert_valid_row(
    engine: Engine, make_event: Callable[..., dict[str, Any]]
) -> None:
    """Insert a well-formed event and confirm it persisted (basic smoke test)."""
    with engine.begin() as conn:
        event = make_event()
        conn.execute(insert(event_store).values(event))
        count = conn.execute(
            select(func.count())  # pylint: disable=not-callable
            .select_from(event_store)
            .where(event_store.c.event_id == event["event_id"])
        ).scalar_one()
        assert count == 1


def test_json_roundtrip(
    engine: Engine, make_event: Callable[..., dict[str, Any]]
) -> None:
    """Payload and metadata should round-trip through the DB unchanged."""
    with engine.begin() as conn:
        event = make_event(payload={"k": ["a", 1, True]}, metadata={"m": {"x": 1}})
        conn.execute(insert(event_store).values(event))
        stored = conn.execute(
            select(event_store.c.payload, event_store.c.metadata).where(
                event_store.c.event_id == event["event_id"]
            )
        ).one()
        assert stored.payload == event["payload"]
        assert stored.metadata == event["metadata"]


def test_unique_stream_version(
    engine: Engine, make_event: Callable[..., dict[str, Any]]
) -> None:
    """(stream_id, version) must be unique."""
    with engine.begin() as conn:
        event = make_event(stream_id="pg-stream", version=1)
        conn.execute(insert(event_store).values(event))
        # inserting same stream/version should fail
        with pytest.raises(IntegrityError):
            conn.execute(
                insert(event_store).values(make_event(stream_id="pg-stream", version=1))
            )


def test_unique_event_id(
    engine: Engine, make_event: Callable[..., dict[str, Any]]
) -> None:
    """event_id must be globally unique."""
    with engine.begin() as conn:
        event = make_event()
        conn.execute(insert(event_store).values(event))
        # inserting with same event_id should fail
        with pytest.raises(IntegrityError):
            conn.execute(
                insert(event_store).values(make_event(event_id=event["event_id"]))
            )


def test_ulid_length_check(
    engine: Engine, make_event: Callable[..., dict[str, Any]]
) -> None:
    """event_id length must be exactly 26 chars (ULID)."""
    with engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.execute(insert(event_store).values(make_event(event_id="x" * 25)))


def test_identity_monotonic(engine: Engine, make_event: Callable[..., dict[str, Any]]):
    """global_seq should increase monotonically across inserts."""
    with engine.begin() as conn:
        a = conn.execute(
            insert(event_store)
            .values(make_event(version=1))
            .returning(event_store.c.global_seq)
        ).scalar_one()
        b = conn.execute(
            insert(event_store)
            .values(make_event(version=2))
            .returning(event_store.c.global_seq)
        ).scalar_one()
        assert a < b


def test_recorded_at_is_tz_aware(
    engine: Engine, make_event: Callable[..., dict[str, Any]]
):
    """recorded_at should be tz-aware UTC per ADR-0009 (server default path)."""
    with engine.begin() as conn:
        event = make_event()
        conn.execute(insert(event_store).values(event))
        timestamp = conn.execute(
            select(event_store.c.recorded_at).where(
                event_store.c.event_id == event["event_id"]
            )
        ).scalar_one()
        # psycopg returns aware datetimes for TIMESTAMP WITH TIME ZONE
        assert_strict_utc(timestamp)


def test_constraints_present(engine: Engine) -> None:
    """Check schema via SQLAlchemy inspector to ensure expected constraint names/columns exist."""
    inspector = inspect(engine)

    unique_constraints_map = {
        u["name"]: tuple(u["column_names"])
        for u in inspector.get_unique_constraints("event_store")
    }

    expected_constraint_name = "uq_event_store_event_id"
    assert expected_constraint_name in unique_constraints_map, (
        f"{expected_constraint_name} not in {unique_constraints_map}"
    )
    assert unique_constraints_map.get(expected_constraint_name) == ("event_id",)

    expected_constraint_name = "uq_event_store_stream_id_version"
    assert expected_constraint_name in unique_constraints_map, (
        f"{expected_constraint_name} not in {unique_constraints_map}"
    )
    assert unique_constraints_map.get(expected_constraint_name) == (
        "stream_id",
        "version",
    )

    check_constraints = {
        c["name"] for c in inspector.get_check_constraints("event_store")
    }

    expected_constraint_name = "ck_event_store_positive_version"
    assert expected_constraint_name in check_constraints, (
        f"{expected_constraint_name} not in {check_constraints}"
    )

    expected_constraint_name = "ck_event_store_event_id_26_char"
    assert expected_constraint_name in check_constraints, (
        f"{expected_constraint_name} not in {check_constraints}"
    )


def test_payload_not_null(
    engine: Engine, make_event: Callable[..., dict[str, Any]]
) -> None:
    """payload must be NOT NULL (None payload should raise IntegrityError)."""
    event = make_event(payload=None)
    assert event["payload"] is None

    with engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.execute(insert(event_store).values(event))


def test_utcdatetime_null_not_allowed(
    engine: Engine, make_event: Callable[..., dict[str, Any]]
) -> None:
    """recorded_at is NOT NULL → inserting None should raise IntegrityError."""
    with engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.execute(
                insert(event_store).values(make_event(version=1, recorded_at=None))
            )


@pytest.mark.parametrize(
    "given_dt, expected_dt, version",
    [
        (  # Naive input → treated as UTC and normalized
            datetime(2024, 1, 1, 12, 0, 0),
            datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            2,
        ),
        (  # Aware input (-07:00 at 05:00) → normalized to 12:00Z
            datetime(2024, 1, 1, 5, 0, 0, tzinfo=timezone(timedelta(hours=-7))),
            datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            3,
        ),
    ],
    ids=["naive->utc", "aware(-0700)->utc"],
)
def test_utcdatetime_bind_variants(
    engine: Engine,
    make_event: Callable[..., dict[str, Any]],
    given_dt: datetime,
    expected_dt: datetime,
    version: int,
) -> None:
    """When a value is supplied, UTCDateTime must normalize it to UTC on bind."""
    with engine.begin() as conn:
        pk = conn.execute(
            insert(event_store)
            .values(make_event(version=version, recorded_at=given_dt))
            .returning(event_store.c.global_seq)
        ).scalar_one()

        got = conn.execute(
            select(event_store.c.recorded_at).where(event_store.c.global_seq == pk)
        ).scalar_one()

    # Strict ADR-0009: tz-aware, UTC
    assert_strict_utc(got)
    # Exact instant match with normalized expectation
    assert got == expected_dt


def test_recorded_at_default_is_strict_utc(
    engine: Engine, make_event: Callable[..., dict[str, Any]]
) -> None:
    """When omitted on insert, recorded_at is set by the DB and must be UTC 'now'."""
    with engine.begin() as conn:
        pk = conn.execute(
            insert(event_store).values(make_event()).returning(event_store.c.global_seq)
        ).scalar_one()
        dt = conn.execute(
            select(event_store.c.recorded_at).where(event_store.c.global_seq == pk)
        ).scalar_one()

    # Enforce strict UTC semantics (tz-aware, +00:00 / Z)
    assert_strict_utc(dt)

    # Sanity check it was set by the server: close to "now" (UTC)
    now = datetime.now(timezone.utc)
    max_time_delay = 5  # within 5s of DB time
    assert abs((now - dt).total_seconds()) < max_time_delay


def test_column_nullability_via_inspector(engine: Engine) -> None:
    """Check schema via SQLAlchemy inspector: expected NOT NULL vs NULL columns."""
    insp = inspect(engine)
    cols = {c["name"]: c for c in insp.get_columns("event_store")}

    # Expected nullability per schema/ADR
    expected_not_null = {
        "global_seq",  # PK
        "stream_id",
        "stream_type",
        "version",
        "event_id",
        "event_type",
        "payload",
        "recorded_at",
    }
    expected_nullable = {"metadata"}

    # Assert sets match exactly
    actual_not_null = {name for name, c in cols.items() if not c["nullable"]}
    actual_nullable = {name for name, c in cols.items() if c["nullable"]}

    assert actual_not_null.issuperset(expected_not_null)
    assert expected_nullable.issubset(actual_nullable)
