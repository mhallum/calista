"""Defines the base interface for versioned catalogs."""

from __future__ import annotations

import abc
from typing import ClassVar, Generic, TypeVar

S = TypeVar("S")  # Snapshot type
R = TypeVar("R")  # Revision type


class VersionedCatalog(abc.ABC, Generic[S, R]):
    """Entities that evolve via published revisions (versions 1..N)."""

    KIND: ClassVar[str]  # e.g., "site", "telescope"
    CODE_ATTR: ClassVar[str]
    REVISION_CLASS: ClassVar[type]
    SNAPSHOT_CLASS: ClassVar[type]

    @abc.abstractmethod
    def get(self, code: str, version: int | None = None) -> S | None:
        """Get an entity by its code.

        Args:
            code: The unique code of the entity.
            version: The specific version of the entity to retrieve.
                If None, retrieves the latest version.

        Returns:
            The entity snapshot if found, otherwise None.

        Note:
            `code` lookup is case-insensitive; implementers should uppercase it.
        """

    @abc.abstractmethod
    def get_head_version(self, code: str) -> int | None:
        """Get the head version of an entity by its code.

        Args:
            code: The unique code of the entity.

        Returns:
            The latest version number if found, otherwise None.

        Note:
            `code` lookup is case-insensitive; implementers should uppercase it.
        """

    @abc.abstractmethod
    def publish(self, revision: R, expected_version: int) -> None:
        """Append a new revision; enforce optimistic lock if expected_version is set.

        Args:
            revision: The entity revision to publish.
            expected_version: The expected head version of the entity for optimistic locking.

        Raises:
            VersionConflictError: If the expected_version does not match the current version.
            NoChangeError: If the revision does not introduce any changes.
        """
