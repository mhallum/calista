"""Event classes for the calista

Domain events stay inside the bounded context and are used for rebuilds and internal projections.
They are emitted by the `Image` model (the aggregate root).
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DomainEvent:
    """Base class for all domain events"""

    image_id: str
    timestamp: datetime
