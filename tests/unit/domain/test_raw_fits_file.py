"""Unit tests for the RawFitsFile aggregate."""

import pytest

from calista.domain import errors, events
from calista.domain.aggregates.raw_fits_file import RawFitsFile, Status
from calista.domain.value_objects import FrameType

# pylint: disable=magic-value-comparison,too-few-public-methods, protected-access
# pylint: disable=redefined-outer-name


@pytest.fixture
def registered_file(make_file_metadata) -> RawFitsFile:
    """Helper to create a registered RawFitsFile aggregate for tests."""
    metadata = make_file_metadata()
    registered = RawFitsFile.register_ingested_file(
        aggregate_id="file-123",
        session_id="session-456",
        sha256=metadata.sha256,
        cas_key=metadata.cas_key,
        size_bytes=metadata.size_bytes,
        ingested_at=metadata.stored_at,
    )
    registered._pending_events.clear()  # Clear events for test isolation
    return registered


class TestRawFitsFileInitialization:
    """Tests for RawFitsFile aggregate initialization."""

    @staticmethod
    def test_initialization_sets_defaults():
        """Test that the aggregate initializes with correct default values."""
        raw_fits_file = RawFitsFile(aggregate_id="file-123")
        assert raw_fits_file.session_id is None
        assert raw_fits_file.metadata is None
        assert raw_fits_file.frame_type is None
        assert raw_fits_file.status is Status.NEW


class TestRawFitsFileRegisterIngestedFile:
    """Tests for the register_ingested_file construction path."""

    @staticmethod
    def test_register_ingested_file_sets_attributes(make_file_metadata):
        """Test that registering an ingested file sets the correct attributes."""

        metadata = make_file_metadata()

        raw_fits_file = RawFitsFile.register_ingested_file(
            aggregate_id="file-456",
            session_id="session-789",
            sha256=metadata.sha256,
            cas_key=metadata.cas_key,
            size_bytes=metadata.size_bytes,
            ingested_at=metadata.stored_at,
        )

        assert raw_fits_file.aggregate_id == "file-456"
        assert raw_fits_file.session_id == "session-789"
        assert raw_fits_file.metadata == metadata
        assert raw_fits_file.status is Status.STORED

    @staticmethod
    def test_adds_event_to_pending_events(make_file_metadata):
        """Test that registering an ingested file enqueues the correct event."""

        metadata = make_file_metadata()

        raw_fits_file = RawFitsFile.register_ingested_file(
            aggregate_id="file-789",
            session_id="session-012",
            sha256=metadata.sha256,
            cas_key=metadata.cas_key,
            size_bytes=metadata.size_bytes,
            ingested_at=metadata.stored_at,
        )

        assert len(raw_fits_file._pending_events) == 1
        event = raw_fits_file._pending_events[0]
        assert isinstance(event, events.RawFitsFileIngested)
        assert event.aggregate_id == "file-789"
        assert event.session_id == "session-012"
        assert event.sha256 == metadata.sha256
        assert event.cas_key == metadata.cas_key
        assert event.size_bytes == metadata.size_bytes
        assert event.ingested_at == metadata.stored_at.isoformat()

    @staticmethod
    def test_does_not_bump_version(make_file_metadata):
        """Test that registering an ingested file does not increment the version."""

        metadata = make_file_metadata()

        raw_fits_file = RawFitsFile.register_ingested_file(
            aggregate_id="file-101",
            session_id="session-202",
            sha256=metadata.sha256,
            cas_key=metadata.cas_key,
            size_bytes=metadata.size_bytes,
            ingested_at=metadata.stored_at,
        )

        assert raw_fits_file.version == 0


class TestRawFitsFileClassifyFrame:
    """Tests for the classify_frame method of RawFitsFile aggregate."""

    @staticmethod
    def test_classify_frame_sets_frame_type(registered_file):
        """Test that classifying a frame sets the correct frame type."""

        registered_file.classify_frame(FrameType.DARK)

        # Verify the frame type and status
        assert registered_file.frame_type == FrameType.DARK
        assert registered_file.status is Status.CATEGORIZED

    @staticmethod
    def test_classify_frame_adds_event_to_pending_events(registered_file):
        """Test that classifying a frame enqueues the correct event."""

        # classify the frame
        registered_file.classify_frame(FrameType.DARK)

        # Verify the event
        assert len(registered_file._pending_events) == 1
        event = registered_file._pending_events[0]
        assert isinstance(event, events.RawFitsFileClassified)
        assert event.frame_type == FrameType.DARK.value

    @staticmethod
    def test_does_not_bump_version(registered_file):
        """Test that classifying a frame does not increment the version."""

        # Classify the frame
        registered_file.classify_frame(FrameType.FLAT)

        # Verify version did not change
        assert registered_file.version == 0

    @staticmethod
    def test_classify_frame_raises_if_file_unstored():
        """Test that classifying a frame on an unstored file raises an error."""

        raw_fits_file = RawFitsFile(aggregate_id="file-303")

        with pytest.raises(
            errors.UnstoredFileClassificationError,
        ) as exc_info:
            raw_fits_file.classify_frame(FrameType.BIAS)

        assert exc_info.value.aggregate_id == "file-303"

        # verify no events were added
        assert len(raw_fits_file._pending_events) == 0

    @staticmethod
    def test_classify_frame_raises_on_duplicate_classification(registered_file):
        """Test that classifying a frame with a different type raises an error."""

        # First classification
        registered_file.classify_frame(FrameType.LIGHT)
        registered_file._pending_events.clear()  # Clear events for test isolation

        # Attempt duplicate classification with different type
        with pytest.raises(
            errors.DuplicateClassificationError,
        ) as exc_info:
            registered_file.classify_frame(FrameType.FLAT)

        error = exc_info.value
        assert error.aggregate_id == "file-123"
        assert error.frame_type == "FrameType.LIGHT"

        # verify no new events were added
        assert len(registered_file._pending_events) == 0

    @staticmethod
    def test_classify_frame_same_classification_idempotent(registered_file):
        """Test that classifying a frame with the same type is idempotent."""

        # First classification
        registered_file.classify_frame(FrameType.DARK)
        registered_file._pending_events.clear()  # Clear events for test isolation

        # Re-classify with the same type
        registered_file.classify_frame(FrameType.DARK)

        # Verify no new events were added
        assert len(registered_file._pending_events) == 0
