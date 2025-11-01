"""Events"""

import abc
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DomainEvent(abc.ABC):
    """Base class for all domain events.
    Requires a way to determine the owning aggregate ID.
    """

    @property
    @abc.abstractmethod
    def aggregate_id(self) -> str:
        """Return the ID of the aggregate this event belongs to."""
