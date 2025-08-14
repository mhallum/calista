"""Unit of Work"""

import abc
from typing import Any

from calista.adapters.image_repository import AbstractImageRepository


class AbstractUnitOfWork(abc.ABC):
    """A unit of work for managing database transactions."""

    images: AbstractImageRepository

    def __enter__(self) -> "AbstractUnitOfWork":
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, *args: Any):
        """Exit the runtime context related to this object."""
        self.rollback()

    def commit(self):
        """Commit the current transaction."""
        self._commit()

    @abc.abstractmethod
    def _commit(self):
        """Commit the current transaction."""

    @abc.abstractmethod
    def rollback(self):
        """Rollback the current transaction."""
