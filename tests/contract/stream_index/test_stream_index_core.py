"""Contract tests for the StreamIndex port.

Behavior under test:
    - lookup() returns None for unknown keys
    - reserve() creates a binding if absent
    - reserve() is idempotent when called again with SAME stream_id
    - reserve() conflicts when the key is already bound to a DIFFERENT stream_id
    - update_version() is monotonic; never decreases
    - update_version() on missing rows is a no-op (does not throw)
"""

from __future__ import annotations

import re
from collections.abc import Iterable

import pytest

from calista.adapters.eventstore.sqlalchemy_adapters.stream_index import (
    SqlAlchemyStreamIndex,
)
from calista.interfaces.stream_index import (
    NaturalKey,
    NaturalKeyAlreadyBound,
    StreamIdAlreadyBound,
    StreamIndex,
)

# Deal with pytest fixtures
# pylint: disable=redefined-outer-name

# --- Fixtures ---


@pytest.fixture(params=["sql_memory", "sql_file", "postgres"])
def stream_index(
    request: pytest.FixtureRequest,
    sqlite_engine_memory,
    sqlite_engine_file,
    postgres_engine,
) -> Iterable[StreamIndex]:
    """Return a fresh StreamIndex instance for the requested backend.

    Supported params:
      - `"sql_memory"` → in-memory SQLite StreamIndex
      - `"sql_file"` → file-based SQLite StreamIndex
      - `"postgres"` → PostgreSQL StreamIndex

    Extend by adding new identifiers to `params` and branching below to
    construct the corresponding backend. Each invocation yields a brand-new
    StreamIndex instance for isolation.
    """

    match request.param:
        case "sql_memory":
            with sqlite_engine_memory.connect() as conn:
                yield SqlAlchemyStreamIndex(conn)
        case "sql_file":
            with sqlite_engine_file.connect() as conn:
                yield SqlAlchemyStreamIndex(conn)
        case "postgres":
            with postgres_engine.connect() as conn:
                yield SqlAlchemyStreamIndex(conn)
        case _:
            raise ValueError(f"unknown store type: {request.param}")


# --- Tests ---


class TestLookup:
    """Tests for the lookup() method."""

    # pylint: disable=too-few-public-methods
    # most lookup tests occur incidentally in reserve tests,
    # so only one explicit test here.

    def _assert_stream_id(
        self, stream_index: StreamIndex, key: NaturalKey, expected_stream_id: str
    ):
        entry = stream_index.lookup(key)
        assert entry is not None
        assert entry.natural_key == key
        assert entry.stream_id == expected_stream_id

    @staticmethod
    def test_lookup_unknown_returns_none(stream_index: StreamIndex):
        """Test that looking up an unknown key returns None."""
        result = stream_index.lookup(NaturalKey("ObservationSession", "unknown-key"))
        assert result is None

    @staticmethod
    def test_lookup_is_scoped_by_kind(stream_index: StreamIndex):
        """Test that lookup() respects the 'kind' field in NaturalKey."""
        # Seed index with two different kinds but same key
        # Same key string, two kinds → two distinct streams
        k1 = NaturalKey("observation_session", "KEY-001")
        k2 = NaturalKey("bias_frame_batch", "KEY-001")
        s1 = "SID-A"
        s2 = "SID-B"
        stream_index.reserve(k1, s1)
        stream_index.reserve(k2, s2)

        # Lookup must respect kind; dropping the kind predicate returns the wrong SID.
        f1 = stream_index.lookup(k1)
        assert f1 is not None
        assert f1.natural_key == k1
        assert f1.stream_id == s1

        f2 = stream_index.lookup(k2)
        assert f2 is not None
        assert f2.natural_key == k2
        assert f2.stream_id == s2


class TestReserve:
    """Tests for the reserve() method."""

    @staticmethod
    def test_reserve_new_entry(stream_index: StreamIndex):
        """Test that reserve() adds a new entry when the key is absent."""

        # reserve
        key = NaturalKey("ObservationSession", "LDT-20240102-DEVENY-R001")
        stream_id = "01HZY0AAAAAAABCDXXXXXX1"
        stream_index.reserve(key, stream_id)

        # Now lookup should see it
        found = stream_index.lookup(key)

        # Assert that the entry was added with proper key, stream_id, and version=0
        assert found is not None
        assert found.natural_key == key
        assert found.stream_id == stream_id
        assert found.version == 0

    @staticmethod
    def test_is_idempotent(stream_index: StreamIndex):
        """Test that reserve() is no-op if the natural key and stream_id are the same."""

        # First reservation
        key = NaturalKey("ObservationSession", "LDT-20240102-DEVENY-R001")
        stream_id = "01HZY0AAAAAAABCDXXXXXX1"
        stream_index.reserve(key, stream_id)

        # Second reservation with the same key and stream_id
        stream_index.reserve(key, stream_id)

        # Assert that entry still exists and is unchanged
        entry = stream_index.lookup(key)
        assert entry is not None
        assert entry.natural_key == key
        assert entry.stream_id == stream_id
        assert entry.version == 0

    @staticmethod
    def test_raises_when_reserving_with_existing_key(stream_index: StreamIndex):
        """Test that reserve() raises if the natural key is already bound to a different stream_id."""

        # Reserve key with stream_id "SID-A"
        first_stream_id = "SID-A"
        key = NaturalKey("ObservationSession", "SITE/2024-01-04/INST/R003")
        stream_index.reserve(key, first_stream_id)

        # Attempt to reserve the same key with a different stream_id "SID-B"
        # Should raise NaturalKeyAlreadyBound
        with pytest.raises(
            NaturalKeyAlreadyBound, match=re.escape(f"{key} → {first_stream_id}")
        ):
            stream_index.reserve(key, "SID-B")

        # Assert that the original entry is still intact
        entry = stream_index.lookup(key)
        assert entry is not None
        assert entry.natural_key == key
        assert entry.stream_id == first_stream_id
        assert entry.version == 0

    @staticmethod
    def test_raises_when_reserving_with_existing_stream_id(stream_index: StreamIndex):
        """Test that reserve() raises if the stream_id is already bound to a different natural key."""

        # Reserve key1 with stream_id "SID-1"
        stream_id = "SID-1"
        key_a = NaturalKey("obs", "A")
        stream_index.reserve(key_a, stream_id)

        # Attempt to reserve a different key2 with the same stream_id "SID-1"
        # Should raise StreamIdAlreadyBound
        key_b = NaturalKey("obs", "B")
        with pytest.raises(
            StreamIdAlreadyBound,
            match=re.escape(f"stream_id {stream_id} already indexed as {key_a}"),
        ):
            stream_index.reserve(key_b, stream_id)

        # Assert that the original entry is still intact
        entry = stream_index.lookup(key_a)
        assert entry is not None
        assert entry.natural_key == key_a
        assert entry.stream_id == stream_id
        assert entry.version == 0


class TestUpdateVersion:
    """Tests for the update_version() method."""

    # --- assertions ---

    @staticmethod
    def _assert_version(stream_index: StreamIndex, key: NaturalKey, expected: int):
        entry = stream_index.lookup(key)
        assert entry is not None
        assert entry.version == expected

    # --- setup helpers ---

    def _seed_with_version(
        self, stream_index: StreamIndex, key: NaturalKey, stream_id: str, version: int
    ):
        stream_index.reserve(key, stream_id)
        stream_index.update_version(stream_id, version)
        self._assert_version(stream_index, key, version)

    # --- tests ---

    def test_scopes_to_target_stream_only(self, stream_index: StreamIndex):
        """Test that advancing one stream_id does not affect others."""

        # seed versions
        self._seed_with_version(stream_index, NaturalKey("obs", "A"), "SID-A", 3)
        self._seed_with_version(stream_index, NaturalKey("obs", "B"), "SID-B", 5)

        # advance A; B must remain unchanged
        stream_index.update_version("SID-A", 7)

        # check results
        self._assert_version(stream_index, NaturalKey("obs", "A"), 7)  # A advances to 7
        self._assert_version(stream_index, NaturalKey("obs", "B"), 5)  # B remains at 5

    @pytest.mark.parametrize("n", [1, 42, 1000], ids=["n=1", "n=42", "n=1000"])
    def test_advance_from_0_to_n(self, stream_index: StreamIndex, n):
        """Test that we can advance from version 0 to some higher number."""

        # Seed index with entry at version 0
        key = NaturalKey("obs", "C")
        stream_index.reserve(key, "SID-C")
        self._assert_version(stream_index, key, 0)

        # Advance to n
        stream_index.update_version("SID-C", n)

        # Assert version is now n
        self._assert_version(stream_index, key, n)

    def test_equal_versions_is_noop(self, stream_index: StreamIndex):
        """Test that updating to the same version is a no-op."""

        # seed index with version 5
        self._seed_with_version(stream_index, NaturalKey("obs", "D"), "SID-D", 5)

        # Advance to same version again
        stream_index.update_version("SID-D", 5)

        # Assert version is still 5
        self._assert_version(stream_index, NaturalKey("obs", "D"), 5)

    def test_decrease_is_noop(self, stream_index: StreamIndex):
        """Test that decreasing the version is a no-op."""

        # seed index with version 10
        self._seed_with_version(stream_index, NaturalKey("obs", "E"), "SID-E", 10)

        # Attempt to decrease to 7
        stream_index.update_version("SID-E", 7)

        # Assert version is still 10
        self._assert_version(stream_index, NaturalKey("obs", "E"), 10)

    @staticmethod
    def test_missing_row_is_noop(stream_index: StreamIndex):
        """Test that updating a missing stream_id is a no-op (does not throw)."""

        stream_index.update_version("some-missing-stream-id", 42)
