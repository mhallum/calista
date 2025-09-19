"""Pytest fixtures for EventStore contract tests."""

from __future__ import annotations

import itertools
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import pytest

from calista.interfaces.eventstore import (
    EventEnvelope,
)

# Simple deterministic 26-char "ULID-like" generator (length-only; not real ULID)
_counter = itertools.count(1)


def make_ulid() -> str:
    """Return a deterministic 26-character ULID-like string (not a real ULID)."""
    return f"{next(_counter):026d}"


@pytest.fixture
def make_envelope() -> Callable[..., EventEnvelope]:
    """Factory for valid envelopes with sensible defaults.

    Args (defaults set for a 'happy path' event):
      - stream_id: str = "S1"
      - stream_type: str = "TestStream"
      - version: int = 1
      - event_type: str = "TestEvent"
      - event_id: str | None = None (auto)
      - payload: dict[str, Any] = {}
      - metadata: dict[str, Any] | None = None
      - recorded_at: datetime | None = now(UTC)
    """

    def _make(
        *,
        stream_id: str = "S1",
        stream_type: str = "TestStream",
        version: int = 1,
        event_type: str = "TestEvent",
        event_id: str | None = None,
        payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        recorded_at: datetime | None = None,
    ) -> EventEnvelope:
        return EventEnvelope(
            stream_id=stream_id,
            stream_type=stream_type,
            version=version,
            event_id=event_id or make_ulid(),
            event_type=event_type,
            payload=payload or {},
            metadata=metadata,
            recorded_at=recorded_at or datetime.now(timezone.utc),
        )

    return _make
