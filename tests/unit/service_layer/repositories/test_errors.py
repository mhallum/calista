"""Tests for repository-related error definitions."""

from calista.service_layer.repositories.errors import AggregateNotFoundError

# pylint: disable=magic-value-comparison


class TestAggregateNotFoundError:
    """Tests for the AggregateNotFoundError exception."""

    @staticmethod
    def test_attributes():
        """Test that the attributes are set correctly."""
        error = AggregateNotFoundError(
            aggregate_type_name="TestAggregate", aggregate_id="12345"
        )
        assert error.aggregate_type_name == "TestAggregate"
        assert error.aggregate_id == "12345"

    @staticmethod
    def test_message():
        """Test that the error message is formatted correctly."""
        error = AggregateNotFoundError(
            aggregate_type_name="TestAggregate", aggregate_id="12345"
        )
        expected_message = "TestAggregate with ID 12345 not found."
        assert str(error) == expected_message
