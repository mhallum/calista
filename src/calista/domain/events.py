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


@dataclass(frozen=True, slots=True)
class RawFitsFileIngested(DomainEvent):
    """Event indicating that a raw FITS file has been ingested."""

    file_id: str
    session_id: str
    sha256: str
    cas_key: str
    size_bytes: int
    ingested_at: str  # UTC datetime in ISO format

    @property
    def aggregate_id(self) -> str:
        return self.file_id


@dataclass(frozen=True, slots=True)
class RawFitsFileClassified(DomainEvent):
    """Event indicating that a raw FITS file has been classified."""

    file_id: str
    frame_type: str

    @property
    def aggregate_id(self) -> str:
        return self.file_id


# Registry of domain event types for deserialization
DOMAIN_EVENT_REGISTRY: dict[str, type[DomainEvent]] = {
    "ObservationSessionRegistered": ObservationSessionRegistered,
    "RawFitsFileIngested": RawFitsFileIngested,
    "RawFitsFileClassified": RawFitsFileClassified,
}
