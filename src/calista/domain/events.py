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


@dataclass(frozen=True, slots=True)
class ObservationSessionRegistered(DomainEvent):
    """Event indicating that an observation session has been registered."""

    session_id: str
    natural_key: str
    facility_code: str
    night_id: str
    segment_number: int

    @property
    def aggregate_id(self) -> str:
        return self.session_id
