"""Defines the SQLAlchemy EventStore adapter package.

This package contains an SQLAlchemy-based implementation of an event store and related components.
The SQLAlchemy event store provides durable storage of events using a relational database,
enabling reliable event sourcing and persistence.
"""

from .eventstore import SqlAlchemyEventStore
from .stream_index import SqlAlchemyStreamIndex

__all__ = [
    "SqlAlchemyEventStore",
    "SqlAlchemyStreamIndex",
]
