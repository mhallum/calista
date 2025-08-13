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


def test_that_registering_an_image_changes_registered_to_true():
    """Test that registering an image changes the registered status to true."""

    image = ImageAggregate(image_id="test_image")
    assert image.registered is False

    image.register(
        session_id="session_1", file_path="path/to/image.jpg", header_meta={}
    )

    assert image.registered is True


def test_that_registering_an_image_is_idempotent():
    """Test that registering an image is idempotent."""

    image = ImageAggregate(image_id="test_image")
    image.register(
        session_id="session_1", file_path="path/to/image.jpg", header_meta={}
    )

    # Registering again should not change the state
    image.register(
        session_id="session_1", file_path="path/to/image.jpg", header_meta={}
    )

    assert len(image.pending_events) == 1
