"""Errors related to catalog interfaces."""


class CatalogError(Exception):
    """Base class for all catalog-related errors."""

    def __init__(self, kind: str, key: str, message: str | None = None) -> None:
        if message is None:
            message = f"{kind} ({key}) catalog error"
        super().__init__(message)


class SnapshotError(CatalogError):
    """Base class for errors related to invalid or inconsistent snapshots."""


class InvalidSnapshotError(SnapshotError):
    """Raised when a snapshot is malformed or violates domain invariants."""

    def __init__(self, kind: str, key: str, reason: str) -> None:
        super().__init__(kind, key, f"Invalid {kind} ({key}) snapshot: {reason}")


class RevisionError(CatalogError):
    """Base class for errors related to invalid or inconsistent revisions."""


class InvalidRevisionError(RevisionError):
    """Raised when a revision is malformed or violates domain invariants."""

    def __init__(self, kind: str, key: str, reason: str) -> None:
        super().__init__(kind, key, f"Invalid {kind} ({key}) revision: {reason}")


class VersionConflictError(RevisionError):
    """Raised when optimistic concurrency check fails."""

    def __init__(self, kind: str, key: str, head: int, expected: int | None) -> None:
        super().__init__(
            kind,
            key,
            f"{kind} ({key}) version conflict: head={head}, expected={expected}",
        )


class NoChangeError(RevisionError):
    """Raised when a patch or revision introduces no changes."""

    def __init__(self, kind: str, key: str) -> None:
        super().__init__(kind, key, f"{kind} ({key}) revision introduces no changes")


class SiteNotFoundError(CatalogError):
    """Raised when a site entry cannot be found in the catalog."""

    def __init__(self, key: str) -> None:
        super().__init__("site", key, f"Site ({key}) not found in catalog")
