"""The domain model"""

import abc

# pylint: disable=too-few-public-methods


class DomainEvent(abc.ABC):
    """Base class for all domain events."""


# AggregateRoot
class ImageAggregate:
    """ImageAggregate represents the aggregate root for image-related operations."""

    def __init__(self, image_id: str):
        self.image_id: str = image_id
        self.pending_events: list[DomainEvent] = []
