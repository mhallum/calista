"""Tests for SimpleIdGenerator."""

import pytest

from calista.adapters.id_generators import SimpleIdGenerator


@pytest.mark.parametrize("length", [5, 10, 15])
def test_simple_id_generator_shape(length):
    """Test that SimpleIdGenerator produces IDs of the correct shape."""
    gen = SimpleIdGenerator(length=length)
    new_id = gen.new_id()
    assert isinstance(new_id, str)
    assert len(new_id) == length
    assert new_id.isdigit()
    assert int(new_id) == 1  # First ID should be "000...001"


def test_simple_id_generator_sequential():
    """Test that SimpleIdGenerator produces sequential IDs."""
    gen = SimpleIdGenerator(length=8)
    ids = [gen.new_id() for _ in range(5)]
    expected_ids = ["00000001", "00000002", "00000003", "00000004", "00000005"]
    assert ids == expected_ids
