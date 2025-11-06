"""EventMapper class unit tests."""

import re
from dataclasses import dataclass

import pytest

from calista.domain.events import DomainEvent
from calista.interfaces.eventstore import EventEnvelope
from calista.service_layer.repositories.event_mapper import EventMapper


@dataclass(frozen=True)
class MockDomainEvent(DomainEvent):
    """A mock domain event for testing purposes."""

    mock_id: str
    text_a: str
    integer_b: int

    @property
    def aggregate_id(self) -> str:
        return self.mock_id


MOCK_REGISTRY: dict[str, type[DomainEvent]] = {"MockDomainEvent": MockDomainEvent}


def test_to_envelope():
    """Test that an EventMapper can convert from a domain event to an event envelope."""
    mapper = EventMapper(event_registry=MOCK_REGISTRY)
    domain_event = MockDomainEvent(mock_id="agg-123", text_a="a", integer_b=42)

    envelope = mapper.to_envelope(
        stream_id="agg-123",
        stream_type="MockAggregate",
        version=1,
        event_id=f"{1:026d}",
        event=domain_event,
    )

    expected_envelope = EventEnvelope(
        stream_id="agg-123",
        stream_type="MockAggregate",
        version=1,
        event_id=f"{1:026d}",
        event_type="MockDomainEvent",
        payload={"mock_id": "agg-123", "text_a": "a", "integer_b": 42},
    )
    assert envelope == expected_envelope


def test_to_domain_event():
    """Test that an EventMapper can convert from an event envelope to a domain event."""
    mapper = EventMapper(event_registry=MOCK_REGISTRY)

    envelope = EventEnvelope(
        stream_id="agg-123",
        stream_type="MockAggregate",
        version=1,
        event_id=f"{1:026d}",
        event_type="MockDomainEvent",
        payload={"mock_id": "agg-123", "text_a": "a", "integer_b": 42},
    )

    domain_event = mapper.to_domain_event(envelope)

    expected_event = MockDomainEvent(mock_id="agg-123", text_a="a", integer_b=42)
    assert domain_event == expected_event


def test_raises_on_unknown_event_type():
    """Test that an EventMapper raises a ValueError for unknown event types."""
    mapper = EventMapper(event_registry=MOCK_REGISTRY)

    envelope = EventEnvelope(
        stream_id="agg-123",
        stream_type="MockAggregate",
        version=1,
        event_id=f"{1:026d}",
        event_type="UnknownEventType",
        payload={},
    )

    with pytest.raises(
        ValueError, match=re.escape("Unknown event type: UnknownEventType")
    ):
        mapper.to_domain_event(envelope)
