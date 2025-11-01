"""Unit tests for domain errors."""

from calista.domain import errors


class TestMismatchedAggregateIdError:
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
