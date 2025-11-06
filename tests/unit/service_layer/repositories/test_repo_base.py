"""Test the generic EventSourcedRepository functionality."""

from dataclasses import dataclass

import pytest

from calista.adapters.eventstore.in_memory_adapters import InMemoryEventStore
from calista.adapters.id_generators import SimpleIdGenerator
from calista.domain import aggregates, events
from calista.service_layer.repositories import EventSourcedRepository, errors
from calista.service_layer.repositories.event_mapper import EventMapper

# pylint: disable=too-few-public-methods,magic-value-comparison

# ============================================================================
#                                   Fakes
# ============================================================================


@dataclass(frozen=True)
class FakeEventA(events.DomainEvent):
    """A fake event for testing purposes."""

    fake_id: str
    value: str

    @property
    def aggregate_id(self) -> str:
        return self.fake_id


@dataclass(frozen=True)
class FakeEventB(events.DomainEvent):
    """Another fake event for testing purposes."""

    fake_id: str
    value: str

    @property
    def aggregate_id(self) -> str:
        return self.fake_id


class FakeAggregate(aggregates.Aggregate):
    """A fake aggregate for testing purposes."""

    STREAM_TYPE = "FakeAggregate"

    def __init__(self, aggregate_id):
        super().__init__(aggregate_id)
        self.something = None
        self.other_thing = None

    def do_something(self, value: str) -> None:
        """A fake method that enqueues a FakeEventA."""
        event = FakeEventA(fake_id=self.aggregate_id, value=value)
        self._enqueue(event)

    def do_other_thing(self, value: str) -> None:
        """A fake method that enqueues a FakeEventB."""
        event = FakeEventB(fake_id=self.aggregate_id, value=value)
        self._enqueue(event)

    def _apply(self, event):
        """Apply an event to the fake aggregate."""
        match event:
            case FakeEventA():
                self.something = event.value
            case FakeEventB():
                self.other_thing = event.value
            case _:
                raise ValueError(f"Unhandled event type: {event['type']}")


FAKE_EVENT_REGISTRY: dict[str, type[events.DomainEvent]] = {
    "FakeEventA": FakeEventA,
    "FakeEventB": FakeEventB,
}

# ============================================================================
#                      Test the EventSourcedRepository
# ============================================================================


def test_load():
    """Test loading an aggregate from events."""

    # Set up repo dependencies
    eventstore = InMemoryEventStore()
    id_generator = SimpleIdGenerator()
    mapper = EventMapper(event_registry=FAKE_EVENT_REGISTRY)

    # Seed an event store with some events for our fake aggregate
    events_list = [
        FakeEventA(fake_id="agg-1", value="first"),
        FakeEventB(fake_id="agg-1", value="second"),
    ]
    eventstore.append(
        [
            mapper.to_envelope(
                stream_id="agg-1",
                stream_type=FakeAggregate.STREAM_TYPE,
                version=i + 1,
                event_id=id_generator.new_id(),
                event=event,
            )
            for i, event in enumerate(events_list)
        ]
    )

    # create the repository
    repo = EventSourcedRepository[FakeAggregate](
        event_store=eventstore,
        event_id_generator=id_generator,
        event_mapper=mapper,
        aggregate_cls=FakeAggregate,
    )

    # load the aggregate
    aggregate = repo.load("agg-1")

    # verify it was rehydrated correctly
    assert aggregate is not None
    assert aggregate.aggregate_id == "agg-1"
    assert aggregate.something == "first"
    assert aggregate.other_thing == "second"


def test_store_events():
    """Test storing aggregate events."""

    # Set up repo dependencies
    eventstore = InMemoryEventStore()
    id_generator = SimpleIdGenerator()
    mapper = EventMapper(event_registry=FAKE_EVENT_REGISTRY)

    # create the repository
    repo = EventSourcedRepository[FakeAggregate](
        event_store=eventstore,
        event_id_generator=id_generator,
        event_mapper=mapper,
        aggregate_cls=FakeAggregate,
    )

    # create a new aggregate and mutate it to generate some events
    aggregate = FakeAggregate(aggregate_id="agg-2")
    aggregate.do_something("alpha")
    aggregate.do_other_thing("beta")

    # store the aggregate's events
    repo.store_events(aggregate)

    # verify the events were stored correctly
    stored_envelopes = list(eventstore.read_stream("agg-2"))
    assert len(stored_envelopes) == 2

    stored_events = [mapper.to_domain_event(env) for env in stored_envelopes]
    assert isinstance(stored_events[0], FakeEventA)
    assert stored_events[0].value == "alpha"
    assert isinstance(stored_events[1], FakeEventB)
    assert stored_events[1].value == "beta"

    reloaded = repo.load("agg-2")
    assert reloaded.something == "alpha"
    assert reloaded.other_thing == "beta"


def test_load_nonexistent_aggregate_raises():
    """Test that loading a nonexistent aggregate raises an error."""

    # Set up repo dependencies
    eventstore = InMemoryEventStore()
    id_generator = SimpleIdGenerator()
    mapper = EventMapper(event_registry=FAKE_EVENT_REGISTRY)

    # create the repository
    repo = EventSourcedRepository[FakeAggregate](
        event_store=eventstore,
        event_id_generator=id_generator,
        event_mapper=mapper,
        aggregate_cls=FakeAggregate,
    )

    # attempt to load a nonexistent aggregate and verify it raises
    with pytest.raises(errors.AggregateNotFoundError) as exc_info:
        repo.load("nonexistent-agg")
    error = exc_info.value
    assert error.aggregate_type_name == "FakeAggregate"
    assert error.aggregate_id == "nonexistent-agg"
