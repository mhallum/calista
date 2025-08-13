"""The domain model"""

from typing import Any

from calista.domain import events

# pylint: disable=too-few-public-methods


# AggregateRoot
class ImageAggregate:
    """ImageAggregate represents the aggregate root for image-related operations."""

    def __init__(self, image_id: str):
        self.image_id: str = image_id
        self.registered: bool = False
        self.pending_events: list[events.DomainEvent] = []
        self.version: int = 0

    def register(self, session_id: str, file_path: str, header_meta: dict[str, Any]):
        """Register a new image."""
        if self.registered:
            return  # idempotent
        event = events.ImageRegistered(
            image_id=self.image_id,
            session_id=session_id,
            file_path=file_path,
            header_meta=header_meta,
        )
        self.apply(event)
        self.pending_events.append(event)

    def apply(self, event: events.DomainEvent):
        """Apply an event to the aggregate."""
        if isinstance(event, events.ImageRegistered):
            self.registered = True
        self.version += 1
