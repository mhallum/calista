"""Testsuite for the ImageAggregate model"""

from calista.domain import events
from calista.domain.model import ImageAggregate


def test_image_aggregate_initializes_with_empty_events():
    """Test that the Image aggregate initializes with an empty events list."""

    image = ImageAggregate(image_id="test_image")
    assert not image.pending_events


def test_that_registering_an_image_adds_event_to_pending_events():
    """Test that registering an image adds an `ImageRegistered` event to the pending events list."""

    image = ImageAggregate(image_id="test_image")
    image.register(
        session_id="session_1", file_path="path/to/image.jpg", header_meta={}
    )

    assert len(image.pending_events) == 1
    assert image.pending_events[0] == events.ImageRegistered(
        image_id="test_image",
        session_id="session_1",
        file_path="path/to/image.jpg",
        header_meta={},
    )
