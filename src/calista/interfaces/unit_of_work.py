"""Unit of Work interface for Calista.

Defines the AbstractUnitOfWork contract: a context-managed unit of work
with an EventStore and abstract commit/rollback methods.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass

from . import catalog
from .eventstore import EventStore


@dataclass(frozen=True, slots=True)
class CatalogBundle:
    """A bundle of catalogs used in a unit of work."""

    site: catalog.SiteCatalog


class AbstractUnitOfWork(abc.ABC):
    """Contract for a transactional unit of work."""

    eventstore: EventStore
    catalogs: CatalogBundle

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
