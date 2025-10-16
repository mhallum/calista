"""Integration tests for adapter specific UUIDv4Generator functionality."""

import uuid

from calista.adapters.id_generators import UUIDv4Generator


def test_uuid4_version_is_4():
    """UUIDv4Generator produces valid UUIDv4 identifiers."""
    gen = UUIDv4Generator()
    value = uuid.UUID(gen.new_id())
    required_version = 4
    assert value.version == required_version
