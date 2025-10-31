"""Defines the in-memory base class for versioned catalogs."""

from __future__ import annotations

import abc
from typing import Generic, TypeVar

from calista.interfaces.catalog.errors import (
    NoChangeError,
    VersionConflictError,
)

from .memory_store import InMemoryCatalogData

S = TypeVar("S")  # Snapshot
R = TypeVar("R")  # Revision

# pylint: disable=consider-using-assignment-expr


class InMemoryVersionedCatalogBase(Generic[S, R]):
    """Shared mechanics for in-memory versioned catalogs: get, head, publish."""

    KIND: str  # e.g., "site", "telescope", "instrument", ...
    CODE_ATTR: str  # e.g., "site_code", "telescope_code", ...
    BUCKET_ATTR: str  # e.g., "sites", "telescopes", ...

    def __init__(
        self,
        data: InMemoryCatalogData,
    ) -> None:
        self._data = data

    @property
    def _bucket(self) -> dict[str, list[S]]:
        return getattr(self._data, self.BUCKET_ATTR)

    def _code_of(self, obj: object) -> str:
        return getattr(obj, self.CODE_ATTR)

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

        snapshots = self._bucket.get(code.upper())
        if snapshots is None:
            return None
        if version is None:
            return snapshots[-1]
        if not 1 <= version <= len(snapshots):
            return None
        return snapshots[version - 1]

    def get_head_version(self, code: str) -> int | None:
        """Get the head version of an entity by its code.

        Args:
            code: The unique code of the entity.

        Returns:
            The latest version number if found, otherwise None.

        Note:
            `code` lookup is case-insensitive; implementers should uppercase it.
        """

        snapshots = self._bucket.get(code.upper())
        if not snapshots:
            return None
        head = snapshots[-1]
        return getattr(head, "version")

    def publish(self, revision: R, expected_version: int) -> None:
        """Append a new revision; enforce optimistic lock if expected_version is set.

        Args:
            revision: The entity revision to publish.
            expected_version: The expected head version of the entity for optimistic locking.

        Raises:
            VersionConflictError: If the expected_version does not match the current version.
            NoChangeError: If the revision does not introduce any changes.
        """

        code = self._code_of(revision)
        snapshots = self._bucket.setdefault(code, [])
        head_version = len(snapshots) if snapshots else 0

        if expected_version != head_version:
            raise VersionConflictError(
                self.KIND,
                code,
                head_version,
                expected_version,
            )

        if snapshots and not revision.get_diff(snapshots[-1]):  # type: ignore[attr-defined]
            raise NoChangeError(self.KIND, code)

        snapshots.append(self._revision_to_snapshot(revision, head_version + 1))

    @abc.abstractmethod
    def _revision_to_snapshot(self, revision: R, version: int) -> S:
        """Convert a revision to a snapshot with the given version number."""
