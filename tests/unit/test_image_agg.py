"""Testsuite for the ImageAggregate model"""

from calista.domain import events
from calista.domain.model import ImageAggregate


def assert_registration_event_applied(image: ImageAggregate):
    """Assert that an ImageRegistered event has been applied.

    This means that registered has been updated to true,
    and raw_path has been set.
    """
    assert image.registered is True, (
        "Expected image to be registered after applying event"
    )
    assert image.raw_path is not None, (
        "Expected raw_path to be set after applying event"
    )


def assert_registration_recorded(image: ImageAggregate):
    """Assert that a registration event was recorded.

    This means that an ImageRegistered event was added to the pending events.
    """
    assert len(image.pending_events) == 1, "Expected exactly one pending event"
    assert isinstance(image.pending_events[0], events.ImageRegistered), (
        "Expected the pending event to be an ImageRegistered event"
    )


def test_image_aggregate_initializes_with_empty_events():
    """Test that the Image aggregate initializes with an empty events list."""

    image = ImageAggregate(image_id="test_image")
    assert not image.pending_events


def test_that_registering_an_image_records_image_registered_event():
    """Test that registering an image records an ImageRegistered event."""

    image = ImageAggregate(image_id="test_image")
    image.register(
        session_id="session_1", file_path="path/to/image.jpg", header_meta={}
    )

    assert_registration_recorded(image)


def test_that_the_register_method_applies_the_appropriate_event():
    """Test that the register method applies and records the appropriate event."""
    image = ImageAggregate(image_id="test_image")
    image.register(
        session_id="session_1", file_path="path/to/image.jpg", header_meta={}
    )

    assert_registration_event_applied(image)


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


def test_that_applying_an_event_bumps_the_version():
    """Test that applying an event bumps the version."""
    image = ImageAggregate(image_id="test_image")
    assert image.version == 0

    event = events.ImageRegistered(
        image_id="test_image",
        session_id="session_1",
        file_path="path/to/image.jpg",
        header_meta={},
    )
    image.apply(event)

    assert image.version == 1


def test_that_applying_image_registered_event_sets_the_correct_path():
    """Test that applying an ImageRegistered event sets the correct path."""

    image = ImageAggregate(image_id="test_image")
    assert image.raw_path is None

    filepath = "path/to/image.jpg"

    event = events.ImageRegistered(
        image_id="test_image",
        session_id="session_1",
        file_path=filepath,
        header_meta={},
    )
    image.apply(event)

    assert image.raw_path == filepath, (
        f"Expected raw_path to be set to the passed file path: {filepath}"
    )
