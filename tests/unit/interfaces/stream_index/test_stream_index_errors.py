"""Unit tests for stream index error classes.

These tests focus on the correctness of exception attributes and messages.
"""

from calista.interfaces.stream_index import errors

# pylint: disable=magic-value-comparison


class TestNaturalKeyAlreadyBound:
    """Tests for NaturalKeyAlreadyBound exception.""" ""

    @staticmethod
    def test_sets_attributes():
        """Attributes are set correctly."""
        exception = errors.NaturalKeyAlreadyBound("key1", "stream1", kind="TestStream")
        assert exception.natural_key == "key1"
        assert exception.stream_id == "stream1"
        assert exception.kind == "TestStream"

    @staticmethod
    def test_message():
        """Error message is formatted correctly."""
        exception = errors.NaturalKeyAlreadyBound("key1", "stream1", kind="TestStream")
        assert (
            str(exception)
            == "Natural key 'key1' is already bound to stream ID 'stream1' for kind 'TestStream'."
        )


class TestStreamIdAlreadyBound:
    """Tests for StreamIdAlreadyBound exception."""

    @staticmethod
    def test_sets_attributes():
        """Attributes are set correctly."""
        exception = errors.StreamIdAlreadyBound("stream1", "key1", "TestStream")
        assert exception.stream_id == "stream1"
        assert exception.natural_key == "key1"
        assert exception.kind == "TestStream"

    @staticmethod
    def test_message():
        """Error message is formatted correctly."""
        exception = errors.StreamIdAlreadyBound("stream1", "key1", "TestStream")
        assert (
            str(exception)
            == "Stream ID 'stream1' is already bound to natural key 'key1' for kind 'TestStream'."
        )
