"""Domain events

Domain events stay inside the bounded context and are used for rebuilds and internal projections.
They are emitted by the `Image` model (the aggregate root).
"""

from dataclasses import dataclass
from typing import Any

# pylint: disable=too-few-public-methods


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events."""


@dataclass(frozen=True)
class ImageRegistered(DomainEvent):
    """Event emitted when an image is registered."""

    image_id: str
    session_id: str
    file_path: str
    header_meta: dict[str, Any]
