"""Unit tests for domain errors."""

from calista.domain import errors


class TestAggregateIdMismatchError:
    """Tests for the AggregateIdMismatchError domain error."""

    @staticmethod
    def test_attributes() -> None:
        """Test that the error attributes includes both aggregate IDs."""
        aggregate_id = "agg-1"
        event_aggregate_id = "agg-2"
        error = errors.AggregateIdMismatchError(aggregate_id, event_aggregate_id)
        assert error.aggregate_id == aggregate_id
        assert error.event_aggregate_id == event_aggregate_id

    @staticmethod
    def test_error_message() -> None:
        """Test that the error message is formatted correctly."""
        aggregate_id = "agg-1"
        event_aggregate_id = "agg-2"
        error = errors.AggregateIdMismatchError(aggregate_id, event_aggregate_id)
        expected_message = (
            f"Event aggregate ID '{event_aggregate_id}' does not match "
            f"aggregate ID '{aggregate_id}'."
        )
        assert str(error) == expected_message


class TestDuplicateClassificationError:
    """Tests for the DuplicateClassificationError domain error."""

    @staticmethod
    def test_attributes() -> None:
        """Test that the error attributes include aggregate ID and frame type."""
        aggregate_id = "file-123"
        frame_type = "BIAS"
        error = errors.DuplicateClassificationError(aggregate_id, frame_type)
        assert error.aggregate_id == aggregate_id
        assert error.frame_type == frame_type

    @staticmethod
    def test_error_message() -> None:
        """Test that the error message is formatted correctly."""
        aggregate_id = "file-123"
        frame_type = "BIAS"
        error = errors.DuplicateClassificationError(aggregate_id, frame_type)
        expected_message = (
            f"File {aggregate_id} has already been classified as {frame_type}."
        )
        assert str(error) == expected_message


class TestUnstoredFileClassificationError:
    """Tests for the UnstoredFileClassificationError domain error."""

    @staticmethod
    def test_attributes() -> None:
        """Test that the error attributes include aggregate ID."""
        aggregate_id = "file-456"
        error = errors.UnstoredFileClassificationError(aggregate_id)
        assert error.aggregate_id == aggregate_id

    @staticmethod
    def test_error_message() -> None:
        """Test that the error message is formatted correctly."""
        aggregate_id = "file-456"
        error = errors.UnstoredFileClassificationError(aggregate_id)
        expected_message = f"File {aggregate_id} must be stored before classification."
        assert str(error) == expected_message
