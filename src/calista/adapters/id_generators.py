"""ID generators for Calista."""

import threading
import uuid

from ulid import monotonic

from calista.interfaces.id_generator import IdGenerator

# pylint: disable=too-few-public-methods


class ULIDGenerator(IdGenerator):
    """Thread-safe monotonic ULID generator.

    ULIDs are unique, lexicographically sortable identifiers.
    They generally consist of a timestamp and a random component.
    This generator uses the `ulid-py` library to create ULIDs.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def new_id(self) -> str:
        """Generate a new ULID (serialized across threads)."""
        with self._lock:
            return str(monotonic.new())


class UUIDv4Generator(IdGenerator):
    """UUIDv4 generator.

    UUIDv4 are universally unique identifiers that are randomly generated.
    They are not guaranteed to be sequential or ordered in any way.
    This generator uses Python's built-in `uuid` library to create UUIDv4 identifiers.
    """

    def new_id(self) -> str:
        """Generate a new UUID."""
        return str(uuid.uuid4())


class SimpleIdGenerator(IdGenerator):
    """A simple ID generator that produces sequential IDs.

    Note:
        Not suitable for production use; primarily for testing and demos.
    """

    def __init__(self, length: int = 26) -> None:
        self._counter = 0
        self._length = length

    def new_id(self) -> str:
        """Generate a new unique identifier."""
        self._counter += 1
        return f"{self._counter:0{self._length}d}"
