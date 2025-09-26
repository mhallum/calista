"""Unit of Work interface for Calista.

Defines the AbstractUnitOfWork contract: a context-managed unit of work
with an EventStore and abstract commit/rollback methods.
"""

from __future__ import annotations

import abc

from .eventstore import EventStore


class AbstractUnitOfWork(abc.ABC):
    """Contract for a transactional unit of work."""

    eventstore: EventStore

    def __enter__(self) -> AbstractUnitOfWork:
        """Enter the unit of work context and return the unit.

        Implementations may acquire transactional resources here.
        """
        return self

    def __exit__(self, *args):
        """Exit the unit of work context.

        Default behavior is to roll back on exit.
        """
        self.rollback()

    @abc.abstractmethod
    def commit(self):
        """Persist changes and finalize the transaction."""

    @abc.abstractmethod
    def rollback(self):
        """Revert changes and clean up transactional resources."""
