"""Testsuite for the ImageAggregate model"""


def test_image_aggregate_initializes_with_empty_events():
    """Test that the Image aggregate initializes with an empty events list."""
    from calista.domain.model import ImageAggregate

    image = ImageAggregate(image_id="test_image")
    assert image.pending_events == []
