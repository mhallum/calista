"""Unit tests for the Aggregate base class."""

from dataclasses import dataclass

from calista.domain.aggregates.base import Aggregate
from calista.domain.events import DomainEvent

# pylint: disable=protected-access,magic-value-comparison,too-few-public-methods


class FakeAggregate(Aggregate):
    """A fake aggregate for testing the base Aggregate class."""

    STREAM_TYPE = "FakeAggregate"

    def __init__(self, aggregate_id: str) -> None:
        super().__init__(aggregate_id)
        self.event_a_applied: bool = False
        self.event_b_applied: bool = False

    def _apply(self, event: DomainEvent) -> None:
        if isinstance(event, FakeEventA):
            self.event_a_applied = True
        elif isinstance(event, FakeEventB):
            self.event_b_applied = True


@dataclass(frozen=True)
class FakeEventA(DomainEvent):
    """A fake event for testing purposes."""


class FakeEventB(DomainEvent):
    """Another fake event for testing purposes."""


class TestAggregateInitialization:
    """Test for the initialization of the Aggregate base class."""

    @staticmethod
    def test_initializes_with_version_zero() -> None:
        """Test that a newly created aggregate has version zero."""
        aggregate = FakeAggregate("agg-1")
        assert aggregate.version == 0

    @staticmethod
    def test_initializes_with_empty_pending_events() -> None:
        """Test that a newly created aggregate has no pending events."""
        aggregate = FakeAggregate("agg-1")
        assert not aggregate._pending_events  # pylint: disable=protected-access

    @staticmethod
    def test_aggregate_id_assignment() -> None:
        """Test that the aggregate ID is assigned correctly."""
        aggregate = FakeAggregate("agg-1")
        assert aggregate.aggregate_id == "agg-1"


class TestAggregateRehydration:
    """Test for the rehydrate class method of Aggregate."""

    @staticmethod
    def test_rehydrates_from_event_stream() -> None:
        """Test that an aggregate can be rehydrated from an event stream."""
        event_stream = [FakeEventA(), FakeEventB()]
        aggregate = FakeAggregate.rehydrate("agg-1", event_stream)

        assert aggregate.aggregate_id == "agg-1"

        # Version bumps for each event applied
        assert aggregate.version == 2

        # Events are applied correctly
        assert aggregate.event_a_applied is True
        assert aggregate.event_b_applied is True

        # No pending events after rehydration
        assert not aggregate._pending_events

    @staticmethod
    def test_rehydrate_version_matches_event_count() -> None:
        """Test that the version after rehydration matches the number of events."""
        num_events = 5
        events: list[DomainEvent] = [
            FakeEventA() if i % 2 == 0 else FakeEventB() for i in range(num_events)
        ]
        agg = FakeAggregate.rehydrate("agg-1", events)
        assert agg.version == len(events)


class TestAggregateEventEnqueueing:
    """Test for the _enqueue method of Aggregate."""

    @staticmethod
    def test_enqueues_and_applies_event() -> None:
        """Test that an event is enqueued and applied correctly."""
        aggregate = FakeAggregate("agg-1")
        event = FakeEventA()

        aggregate._enqueue(event)

        assert aggregate._pending_events == [event]
        assert aggregate.event_a_applied is True

    @staticmethod
    def test_enqueue_does_not_change_version() -> None:
        """Test that enqueuing an event does not change the version."""
        aggregate = FakeAggregate("agg-1")
        initial_version = aggregate.version

        aggregate._enqueue(FakeEventA())

        assert aggregate.version == initial_version


class TestAggregateDequeueUncommitted:
    """Test for the dequeue_uncommitted method of Aggregate."""

    @staticmethod
    def test_dequeues_uncommitted_events() -> None:
        """Test that uncommitted events are dequeued correctly."""
        aggregate = FakeAggregate("agg-1")
        event_a = FakeEventA()
        event_b = FakeEventB()

        aggregate._enqueue(event_a)
        aggregate._enqueue(event_b)

        uncommitted = aggregate.dequeue_uncommitted()

        assert uncommitted == [event_a, event_b]
        assert not aggregate._pending_events
