"""Base class for all aggregates."""

import abc
from collections.abc import Sequence
from typing import ClassVar, TypeVar

from calista.domain.errors import AggregateIdMismatchError
from calista.domain.events import DomainEvent

# pylint: disable=consider-using-assignment-expr

A = TypeVar("A", bound="Aggregate")


class Aggregate(abc.ABC):
    """Generic base class for all aggregates."""

    STREAM_TYPE: ClassVar[str]
    """A string identifier for the type of event stream this aggregate uses.

    Concrete aggregate implementations must set this to distinguish their event streams.
    """

    def __init__(self, aggregate_id: str) -> None:
        self.aggregate_id: str = aggregate_id
        self._version: int = 0
        self._pending_events: list[DomainEvent] = []

    # --- Construction Paths ---

    @classmethod
    def rehydrate(
        cls: type[A], aggregate_id: str, event_stream: Sequence[DomainEvent]
    ) -> A:
        """Rebuild an aggregate from its past events.

        Args:
            aggregate_id: The ID of the aggregate to rebuild.
            event_stream: A sequence of events to apply to the aggregate in order.

        Returns:
            An instance of the aggregate rebuilt to the state represented by the event stream.
        Raises:
            AggregateIdMismatchError: If any event in the stream has an aggregate_id
                that does not match the provided aggregate_id.
            UnknownEventType: if the aggregate does not know how to handle one of the events
        """
        aggregate = cls(aggregate_id)
        for event in event_stream:
            aggregate._apply_checked(event)  # raises the errors as needed
            aggregate._version += 1
        return aggregate

    # --- Event Application ---

    def _apply_checked(self, event: DomainEvent) -> None:
        """Internal gate. Do not override.

        Performs aggregate ID check before applying event.
        """
        if event.aggregate_id != self.aggregate_id:
            raise AggregateIdMismatchError(self.aggregate_id, event.aggregate_id)
        self._apply(event)

    @abc.abstractmethod
    def _apply(self, event: DomainEvent) -> None:
        """Apply an event to the aggregate.

        Args:
            event: The event to apply.
        Raises:
            UnknownEventType: If the concrete aggregate does not implement handling logic for
                the event type.

        Note: ID matching is automatically enforced by the base class.
        """

    # --- Plumbing ---

    def _enqueue(self, event: DomainEvent) -> None:
        self._apply_checked(event)
        self._pending_events.append(event)

    def dequeue_uncommitted(self) -> list[DomainEvent]:
        """Dequeue all uncommitted events.

        Returns:
            A list of all uncommitted events since the last call to this method.

        Note: This is NOT thread-safe. It is the caller's responsibility to ensure
        that no other operations are performed on the aggregate between calls to this
        method.
        """

        uncommitted_events = self._pending_events
        self._pending_events = []
        return uncommitted_events

    @property
    def version(self) -> int:
        """The current version of the aggregate."""
        return self._version
