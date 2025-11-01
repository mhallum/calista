"""Fixtures for generating test data."""

import datetime
import itertools
from collections.abc import Callable
from typing import Any

import pytest

from calista.interfaces.eventstore import (
    EventEnvelope,
)

# pylint: disable=too-many-arguments

_counter = itertools.count(1)  # for ulid_like()


def ulid_like() -> str:
    """Return a deterministic 26-character ULID-like string.

    Good enough for tests that assert length/uniqueness; not lexicographically sortable.
    """
    return f"{next(_counter):026d}"


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
        recorded_at: datetime.datetime | None = None,
    ) -> EventEnvelope:
        return EventEnvelope(
            stream_id=stream_id,
            stream_type=stream_type,
            version=version,
            event_id=event_id or ulid_like(),
            event_type=event_type,
            payload=payload or {},
            metadata=metadata,
            recorded_at=recorded_at or datetime.datetime.now(datetime.timezone.utc),
        )

    return _make


@pytest.fixture
def make_site_params():
    """Factory for site parameters with sensible defaults.

    Args (defaults):
        - source: str | None = "Some Test Source"
        - timezone: str | None = "America/New_York"
        - lat_deg: float | None = 34.0
        - lon_deg: float | None = 30.0
        - elevation_m: float | None = 100.0
        - mpc_code: str | None = "XXX"
        - comment: str | None = None

    Note:
        The default coordinates (lat_deg=34.0, lon_deg=30.0) and elevation
        (elevation_m=100.0) are arbitrary and do not correspond to a real-world
        location. Adjust these values as needed for tests requiring realistic site data.

    Defaults can be overridden by keyword arguments.
    """

    def _make(
        site_code: str,
        name: str,
        *,
        source: str | None = "Some Test Source",
        timezone: str | None = "America/New_York",
        lat_deg: float | None = 34.0,
        lon_deg: float | None = 30.0,
        elevation_m: float | None = 100.0,
        mpc_code: str | None = "XXX",
        comment: str | None = None,
    ) -> dict:
        return {
            "site_code": site_code,
            "name": name,
            "source": source,
            "timezone": timezone,
            "lat_deg": lat_deg,
            "lon_deg": lon_deg,
            "elevation_m": elevation_m,
            "mpc_code": mpc_code,
            "comment": comment,
        }

    return _make


@pytest.fixture
def make_telescope_params():
    """Factory for telescope parameters with sensible defaults.

    Args (defaults):
        - source: str | None = "Some Test Source"
        - aperture_m: float | None = 1.0
        - comment: str | None = None

    defaults can be overridden by keyword arguments.
    """

    def _make(
        telescope_code: str,
        name: str,
        *,
        source: str | None = "Some Test Source",
        aperture_m: float | None = 1.0,
        comment: str | None = None,
    ) -> dict:
        return {
            "telescope_code": telescope_code,
            "name": name,
            "source": source,
            "aperture_m": aperture_m,
            "comment": comment,
        }

    return _make


@pytest.fixture
def make_instrument_params():
    """Factory for instrument parameters with sensible defaults.

    Args (defaults):
        - source: str | None = "Some Test Source"
        - mode: str | None = "Imaging"
        - comment: str | None = None

    defaults can be overridden by keyword arguments.
    """

    def _make(
        instrument_code: str,
        name: str,
        *,
        source: str | None = "Some Test Source",
        mode: str | None = "Imaging",
        comment: str | None = None,
    ) -> dict:
        return {
            "instrument_code": instrument_code,
            "name": name,
            "source": source,
            "mode": mode,
            "comment": comment,
        }

    return _make
