"""Unit tests framework for EventEnvelope and EventEnvelopeBatch.

Tests that invariants are enforced at construction time.
"""

from datetime import datetime, timedelta, timezone

import pytest

from calista.interfaces.eventstore import (
    EventEnvelope,
    EventEnvelopeBatch,
    InvalidEnvelopeError,
)


class TestEventEnvelope:
    """Unit tests for EventEnvelope invariants."""

    @staticmethod
    def test_event_id_not_26_char_raises_error(make_event):
        """Test that event_id not 26 chars raises InvalidEnvelopeError."""
        with pytest.raises(
            InvalidEnvelopeError, match="event_id must be a 26-character ULID"
        ):
            EventEnvelope(**make_event(event_id="short"))

    @pytest.mark.parametrize("bad_version", [-1, 0], ids=["negative", "zero"])
    @staticmethod
    def test_version_not_positive_raises_error(make_event, bad_version):
        """Test that version <= 0 raises InvalidEnvelopeError."""
        with pytest.raises(InvalidEnvelopeError, match="version must be >= 1"):
            EventEnvelope(**make_event(version=bad_version))

    @pytest.mark.parametrize("bad_global_seq", [-1, 0], ids=["negative", "zero"])
    @staticmethod
    def test_global_seq_not_positive_raises_error(make_event, bad_global_seq):
        """Test that global_seq <= 0 raises InvalidEnvelopeError."""
        with pytest.raises(InvalidEnvelopeError, match="global_seq must be >= 1"):
            EventEnvelope(**make_event(global_seq=bad_global_seq))

    @staticmethod
    def test_non_timezone_aware_recorded_at_raises_error(make_event):
        """Test that naive recorded_at raises InvalidEnvelopeError."""

        with pytest.raises(InvalidEnvelopeError, match="recorded_at must be tz-aware"):
            EventEnvelope(**make_event(recorded_at=datetime.now()))

    @staticmethod
    def test_non_utc_recorded_at_raises_error(make_event):
        """Test that non-UTC recorded_at raises InvalidEnvelopeError."""
        pst = timezone(timedelta(hours=-8))
        with pytest.raises(InvalidEnvelopeError, match="recorded_at must be UTC"):
            EventEnvelope(**make_event(recorded_at=datetime.now(pst)))

    @pytest.mark.parametrize(
        "stream_id, stream_type, event_type",
        [
            ("", "", ""),
            ("", "stream_type", "event_type"),
            ("stream_id", "", "event_type"),
            ("stream_id", "stream_type", ""),
            ("stream_id", "", ""),
            ("", "stream_type", ""),
            ("", "", "event_type"),
        ],
        ids=[
            "all empty",
            "stream_id is empty",
            "stream_type is empty",
            "event_type is empty",
            "only stream_id non-empty",
            "only stream_type non-empty",
            "only event_type non-empty",
        ],
    )
    @staticmethod
    def test_stream_id_stream_type_and_event_type_must_be_non_empty(
        stream_id, stream_type, event_type, make_event
    ):
        """Test that stream_id, stream_type, and event_type must be non-empty."""
        with pytest.raises(
            InvalidEnvelopeError,
            match="stream_id, stream_type, and event_type must be non-empty",
        ):
            EventEnvelope(
                **make_event(
                    stream_id=stream_id, stream_type=stream_type, event_type=event_type
                )
            )


class TestEventEnvelopeBatch:
    """Unit tests for EventEnvelopeBatch invariants."""

    @staticmethod
    def test_empty_batch_raises_error():
        """Test that empty batch raises InvalidEnvelopeError."""
        with pytest.raises(InvalidEnvelopeError, match="Empty batch is not allowed."):
            EventEnvelopeBatch(
                stream_id="test_stream_id", stream_type="test_stream_type", events=[]
            )

    @staticmethod
    def test_mixed_streams_raises_error(make_event):
        """Test that mixed stream_ids in batch raises InvalidEnvelopeError."""
        e1 = EventEnvelope(**make_event(stream_id="A", version=1))
        e2 = EventEnvelope(**make_event(stream_id="B", version=1))
        with pytest.raises(
            InvalidEnvelopeError,
            match="Mixed streams in a single batch",
        ):
            EventEnvelopeBatch.from_events((e1, e2))

    @staticmethod
    def test_non_contiguous_versions_raises_error(make_event):
        """Test that non-contiguous versions in batch raises InvalidEnvelopeError."""
        e1 = EventEnvelope(**make_event(version=1))
        e3 = EventEnvelope(**make_event(version=3))
        with pytest.raises(
            InvalidEnvelopeError,
            match="Versions in batch must be contiguous and ordered.",
        ):
            EventEnvelopeBatch.from_events((e1, e3))

    @staticmethod
    def test_global_seq_set_raises_error(make_event):
        """Test that global_seq set before persistence raises InvalidEnvelopeError."""
        e1 = EventEnvelope(**make_event(version=1, global_seq=1))
        e2 = EventEnvelope(**make_event(version=2))
        with pytest.raises(
            InvalidEnvelopeError,
            match="global_seq must be None before persistence.",
        ):
            EventEnvelopeBatch.from_events((e1, e2))

    @staticmethod
    def test_duplicate_event_ids_raises(make_event):
        """Test that duplicate event_id in batch raises InvalidEnvelopeError."""
        e1 = EventEnvelope(
            **make_event(version=1, event_id="00000000000000000000000001")
        )
        e2 = EventEnvelope(
            **make_event(version=2, event_id="00000000000000000000000001")
        )
        with pytest.raises(
            InvalidEnvelopeError,
            match="Duplicate event_id within batch.",
        ):
            EventEnvelopeBatch.from_events((e1, e2))
