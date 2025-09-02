"""Module for providing time related assertion helpers"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def assert_strict_utc(dt: datetime) -> None:
    """Fails if dt is not tz-aware UTC.
    This catches accidental astimezone(None) (local time) even if offset is 0.
    """
    # tz-aware
    assert dt.tzinfo is not None, "timestamp must be tz-aware"
    # exactly zero offset
    assert dt.utcoffset() == timedelta(0), (
        f"expected UTC offset 0, got {dt.utcoffset()}"
    )
    # format must look UTC (no local offset)
    iso = dt.isoformat()
    assert iso.endswith("+00:00") or iso.endswith("Z"), (
        f"expected RFC3339 UTC, got {iso}"
    )
    # in practice psycopg returns timezone.utc
    assert dt.tzinfo is timezone.utc, "tzinfo should be datetime.timezone.utc"
