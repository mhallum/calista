"""Tests for SqlAlchemyStreamIndex functionality.

This file contains tests that are specific to the SqlAlchemyStreamIndex
implementation and are not covered by the generic StreamIndex contract tests.
"""

from calista.adapters.eventstore.stream_index import (
    SqlAlchemyStreamIndex,
)
from calista.interfaces.stream_index import NaturalKey


def test_lookup_by_stream_non_existent(sqlite_engine_memory):
    """Test that looking up by stream ID that does not exist returns None."""

    with sqlite_engine_memory.connect() as connection:
        stream_index = SqlAlchemyStreamIndex(connection)

        # seed index with one entry to make sure lookup does not falsely match
        # something that isn't there
        stream_index.reserve(NaturalKey("obs", "A"), "SID-A")

        # lookup by a stream ID that does not exist
        result = stream_index._lookup_by_stream("NON-EXISTENT-SID")  # pylint: disable=protected-access
        assert result is None


def test_lookup_by_stream_existing(sqlite_engine_memory):
    """Test that looking up by stream ID that exists returns the correct IndexEntry."""

    with sqlite_engine_memory.connect() as connection:
        stream_index = SqlAlchemyStreamIndex(connection)

        # seed index with one entry
        natural_key = NaturalKey("obs", "A")
        stream_id = "SID-A"
        stream_index.reserve(natural_key, stream_id)

        # lookup by the existing stream ID
        result = stream_index._lookup_by_stream(stream_id)  # pylint: disable=protected-access
        assert result is not None
        assert result.natural_key == natural_key
        assert result.stream_id == stream_id
        assert result.version == 0  # initial version should be 0
