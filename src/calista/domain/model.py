"""The domain model"""

import abc
from dataclasses import dataclass
from typing import Any

# pylint: disable=too-few-public-methods


class DomainEvent(abc.ABC):
    """Base class for all domain events."""


@dataclass(frozen=True)
class ImageRegistered(DomainEvent):
    """Event emitted when an image is registered."""

    image_id: str
    session_id: str
    file_path: str
    header_meta: dict[str, Any]


# AggregateRoot
class ImageAggregate:
    """ImageAggregate represents the aggregate root for image-related operations."""

    def __init__(self, image_id: str):
        self.image_id: str = image_id
        self.pending_events: list[DomainEvent] = []

    def register(self, session_id: str, file_path: str, header_meta: dict[str, Any]):
        """Register a new image."""
        event = ImageRegistered(
            image_id=self.image_id,
            session_id=session_id,
            file_path=file_path,
            header_meta=header_meta,
        )
        self.pending_events.append(event)
