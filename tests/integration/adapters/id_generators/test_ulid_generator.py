"""Integration tests for adapter specific ULIDGenerator functionality."""

from calista.adapters.id_generators import ULIDGenerator


def test_ulid_has_len_26():
    """ULIDs are 26 characters long."""
    gen = ULIDGenerator()
    s = gen.new_id()
    required_length = 26
    assert len(s) == required_length
