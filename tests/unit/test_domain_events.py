"""Testsuite for domain events"""

from datetime import datetime

import pytest

from calista.domain.events import DomainEvent


def test_domain_event_model_creation():
    """Test the DomainEvent base class."""

    image_id = "test_image"
    timestamp = datetime.fromisoformat("2023-10-01T00:00:00Z")

    event = DomainEvent(
        image_id="test_image",
        timestamp=datetime.fromisoformat("2023-10-01T00:00:00Z"),
    )

    assert event.image_id == image_id
    assert event.timestamp == timestamp


def test_domain_event_immutability():
    """Test that the DomainEvent base class is immutable"""

    image_id = "test_image"
    timestamp = datetime.fromisoformat("2023-10-01T00:00:00Z")

    event = DomainEvent(
        image_id=image_id,
        timestamp=timestamp,
    )

    with pytest.raises(AttributeError):
        event.image_id = "new_image_id"  # type: ignore

    with pytest.raises(AttributeError):
        event.timestamp = datetime.fromisoformat("2023-10-02T00:00:00Z")  # type: ignore
