"""Defines the in-memory event store adapter package.

This package contains an in-memory implementation of an event store and related components.
The in-memory event store is suitable for testing, prototyping, and scenarios where durability
is not a concern. It provides fast, ephemeral storage of events that are lost when the instance
is discarded.
"""

from .eventstore import InMemoryEventStore
from .stream_index import InMemoryStreamIndex

__all__ = ["InMemoryEventStore", "InMemoryStreamIndex"]
