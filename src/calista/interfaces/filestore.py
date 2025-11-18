"""File store interface definitions."""

import abc
import os
from dataclasses import dataclass
from typing import BinaryIO

PathLike = str | os.PathLike[str]


@dataclass
class BlobStats:
    """Class representing the metadata of a blob."""

    size_bytes: int
    sha256: str


class FileStore(abc.ABC):
    """Abstract base class for CAS file storage operations."""

    # --- Core Operations ---

    @abc.abstractmethod
    def store(self, fileobj: BinaryIO) -> BlobStats:
        """Store bytes from a binary file-like object in the CAS filestore.

        The filestore reads from the stream's *current position* until EOF.
        Callers are responsible for seeking to the desired position, typically 0.

        Args:
            fileobj (BinaryIO): A binary file-like object to read data from.

        Returns:
            BlobStats: Metadata about the stored blob.

        Note:
            If a file with the same SHA-256 hash already exists in the filestore,
            it will not be duplicated. Instead, the metadata of the existing
            file will be returned.
        """

    @abc.abstractmethod
    def open_read(self, sha256: str) -> BinaryIO:
        """Open a file from the file store for reading in binary mode.

        Args:
            sha256 (str): The content-addressable storage key of the file (SHA-256).

        Returns:
            BinaryIO: A binary file-like object for reading the blob.

        Raises:
            FileNotFoundError: If the file does not exist in the filestore.
            ValueError: If the provided SHA-256 key is invalid.

        Example:
            with file_store.open_read(sha256) as f:
                data = f.read()
        """

    # --- Convenience Methods ---

    @abc.abstractmethod
    def exists(self, sha256: str) -> bool:
        """Check if a file exists in the file store.

        Args:
            sha256 (str): The content-addressable storage key of the file (SHA-256).

        Raises:
            ValueError: If the provided SHA-256 key is invalid.

        Returns:
            bool: True if the file exists, False otherwise.
        """
