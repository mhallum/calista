"""Interface for ID generators."""

import abc

# pylint: disable=too-few-public-methods


class IdGenerator(abc.ABC):
    """Contract for an ID generator."""

    @abc.abstractmethod
    def new_id(self) -> str:
        """Generate a new unique identifier."""
