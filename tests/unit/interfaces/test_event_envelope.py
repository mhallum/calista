"""Unit tests framework for EventEnvelope and EventEnvelopeBatch.

Tests that invariants are enforced at construction time.
"""

import pytest

from calista.interfaces.eventstore import (
    EventEnvelope,
    EventEnvelopeBatch,
    InvalidEnvelopeError,
)


class TestEventEnvelope:
    def test_event_id_not_26_char_raises_error(self, make_event):
        with pytest.raises(
            InvalidEnvelopeError, match="event_id must be a 26-character ULID"
        ):
            EventEnvelope(**make_event(event_id="short"))

    @pytest.mark.parametrize("bad_version", [-1, 0], ids=["negative", "zero"])
    def test_version_not_positive_raises_error(self, make_event, bad_version):
        with pytest.raises(InvalidEnvelopeError, match="version must be >= 1"):
            EventEnvelope(**make_event(version=bad_version))

    @pytest.mark.parametrize("bad_global_seq", [-1, 0], ids=["negative", "zero"])
    def test_global_seq_not_positive_raises_error(self, make_event, bad_global_seq):
        with pytest.raises(InvalidEnvelopeError, match="global_seq must be >= 1"):
            EventEnvelope(**make_event(global_seq=bad_global_seq))

    def test_non_timezone_aware_recorded_at_raises_error(self, make_event):
        from datetime import datetime

        with pytest.raises(InvalidEnvelopeError, match="recorded_at must be tz-aware"):
            EventEnvelope(**make_event(recorded_at=datetime.now()))

    def test_non_utc_recorded_at_raises_error(self, make_event):
        from datetime import datetime, timedelta, timezone

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
    def test_stream_id_stream_type_and_event_type_must_be_non_empty(
        self, stream_id, stream_type, event_type, make_event
    ):
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
    def test_empty_batch_raises_error(self):
        with pytest.raises(InvalidEnvelopeError, match="Empty batch is not allowed."):
            EventEnvelopeBatch(
                stream_id="test_stream_id", stream_type="test_stream_type", events=[]
            )

    def test_mixed_streams_raises_error(self, make_event):
        e1 = EventEnvelope(**make_event(stream_id="A", version=1))
        e2 = EventEnvelope(**make_event(stream_id="B", version=1))
        with pytest.raises(
            InvalidEnvelopeError,
            match="Mixed streams in a single batch",
        ):
            EventEnvelopeBatch.from_events((e1, e2))

    def test_non_contiguous_versions_raises_error(self, make_event):
        e1 = EventEnvelope(**make_event(version=1))
        e3 = EventEnvelope(**make_event(version=3))
        with pytest.raises(
            InvalidEnvelopeError,
            match="Versions in batch must be contiguous and ordered.",
        ):
            EventEnvelopeBatch.from_events((e1, e3))

    def test_global_seq_set_raises_error(self, make_event):
        e1 = EventEnvelope(**make_event(version=1, global_seq=1))
        e2 = EventEnvelope(**make_event(version=2))
        with pytest.raises(
            InvalidEnvelopeError,
            match="global_seq must be None before persistence.",
        ):
            EventEnvelopeBatch.from_events((e1, e2))

    def test_duplicate_event_ids_raises(self, make_event):
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
