"""Module for event-sourced repositories."""

from __future__ import annotations

from typing import Generic, TypeVar

from calista.domain.aggregates import Aggregate  # pylint: disable=unused-import

# pylint: disable=unused-import
from calista.interfaces.eventstore import EventStore
from calista.interfaces.id_generator import IdGenerator

from .errors import AggregateNotFoundError
from .event_mapper import EventMapper

# pylint: disable=too-few-public-methods

# ============================================================================
#                      Generic Event-Sourced Keyed Repository
# ============================================================================


T = TypeVar("T", bound="Aggregate")


class EventSourcedRepository(Generic[T]):
    """Event-sourced repository for aggregates.

    This is essentially a wrapper around an event store that loads and saves events
    for aggregates of a specific type.
    """

    def __init__(
        self,
        event_store: EventStore,
        event_id_generator: IdGenerator,
        event_mapper: EventMapper | None = None,
        *,
        aggregate_cls: type[T],
    ) -> None:
        self.event_store = event_store
        self.event_id_generator = event_id_generator
        self.event_mapper = event_mapper if event_mapper is not None else EventMapper()
        self.aggregate_cls = aggregate_cls

    # --- Loads ---

    def load(self, aggregate_id: str) -> T:
        """Get an aggregate from its ID.

        Args:
            aggregate_id: The ID of the aggregate to retrieve.
        Raises:
            AggregateNotFoundError: If the aggregate does not exist.
        Returns:
            The aggregate
        """

        if not (
            envelopes := list(self.event_store.read_stream(stream_id=aggregate_id))
        ):
            raise AggregateNotFoundError(
                aggregate_type_name=self.aggregate_cls.__name__,
                aggregate_id=aggregate_id,
            )

        events = [self.event_mapper.to_domain_event(envelope) for envelope in envelopes]
        return self.aggregate_cls.rehydrate(aggregate_id, events)

    # --- Saves ---

    def store_events(self, aggregate: T) -> None:
        """Save the aggregates events to its stream."""

        events = aggregate.dequeue_uncommitted()
        envelopes = [
            self.event_mapper.to_envelope(
                stream_id=aggregate.aggregate_id,
                stream_type=aggregate.STREAM_TYPE,
                version=aggregate.version + i,
                event_id=self.event_id_generator.new_id(),
                event=event,
            )
            for i, event in enumerate(events, start=1)
        ]

        self.event_store.append(envelopes)
