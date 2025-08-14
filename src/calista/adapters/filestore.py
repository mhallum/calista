"""File store adapter for handling file storage and retrieval."""

import abc
from pathlib import Path


class AbstractFileStore(abc.ABC):
    """Abstract base class for file storage backends."""

    def __init__(self, root: Path):
        self.root = root

    @abc.abstractmethod
    def put(self, src: Path, dest_rel: str):
        """Store a file in the file store."""

    @abc.abstractmethod
    def exists(self, dest_rel: str) -> bool:
        """Check if a file exists in the store."""

    def uri(self, dest_rel: str) -> str:
        """Get the URI of a file in the store."""
        return str(self.root / dest_rel)
