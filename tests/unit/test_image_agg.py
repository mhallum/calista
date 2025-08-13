"""Testsuite for the ImageAggregate model"""

from calista.domain.model import ImageAggregate


def test_image_aggregate_initializes_with_empty_events():
    """Test that the Image aggregate initializes with an empty events list."""

    image = ImageAggregate(image_id="test_image")
    assert not image.pending_events
