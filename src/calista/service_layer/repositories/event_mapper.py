"""Conversions between DomainEvents and EventEnvelopes."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

from calista.domain.events import DOMAIN_EVENT_REGISTRY
from calista.interfaces.eventstore import EventEnvelope

if TYPE_CHECKING:
    from calista.domain.events import DomainEvent


class EventMapper:
    """Maps between DomainEvents and EventEnvelopes."""

    def __init__(
        self, event_registry: dict[str, type[DomainEvent]] | None = None
    ) -> None:
        self.event_registry = (
            event_registry if event_registry is not None else DOMAIN_EVENT_REGISTRY
        )

    @staticmethod
    def to_envelope(
        stream_id: str,
        stream_type: str,
        version: int,
        event_id: str,
        event: DomainEvent,
    ) -> EventEnvelope:
        """Convert a DomainEvent to an EventEnvelope."""
        event_type = type(event).__name__
        payload = asdict(event)
        return EventEnvelope(
            stream_id=stream_id,
            stream_type=stream_type,
            version=version,
            event_id=event_id,
            event_type=event_type,
            payload=payload,
        )

    def to_domain_event(self, envelope: EventEnvelope) -> DomainEvent:
        """Convert an EventEnvelope back to a DomainEvent."""
        if not (cls := self.event_registry.get(envelope.event_type)):
            raise ValueError(f"Unknown event type: {envelope.event_type}")
        return cls(**envelope.payload)
