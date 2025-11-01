"""Base class for all aggregates."""

import abc
from collections.abc import Iterable
from typing import ClassVar, TypeVar

from calista.domain.events import DomainEvent

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
        cls: type[A], aggregate_id: str, event_stream: Iterable[DomainEvent]
    ) -> A:
        """Rebuild an aggregate from its past events."""
        aggregate = cls(aggregate_id)
        for event in event_stream:
            aggregate._apply(event)
            aggregate._version += 1
        return aggregate

    # --- Event Application ---

    @abc.abstractmethod
    def _apply(self, event: DomainEvent) -> None:
        """Apply an event to the aggregate."""

    # --- Plumbing ---

    def _enqueue(self, event: DomainEvent) -> None:
        self._pending_events.append(event)
        self._apply(event)

    def dequeue_uncommitted(self) -> list[DomainEvent]:
        """Dequeue all uncommitted events.

        Note: This is NOT thread-safe. It is the caller's responsibility to ensure
        that no other operations are performed on the aggregate between calls to this
        method.
        """
        uncommitted_events, self._pending_events = self._pending_events, []
        return uncommitted_events

    @property
    def version(self) -> int:
        """The current version of the aggregate."""
        return self._version
