"""Errors related to catalog interfaces."""


class CatalogError(Exception):
    """Base class for all catalog-related errors."""

    def __init__(self, kind: str, key: str, message: str | None = None) -> None:
        if message is None:
            message = f"{kind} ({key}) catalog error"
        super().__init__(message)


class RevisionError(CatalogError):
    """Base class for errors related to invalid or inconsistent revisions."""


class InvalidRevisionError(RevisionError):
    """Raised when a revision is malformed or violates domain invariants."""

    def __init__(self, kind: str, key: str, reason: str) -> None:
        super().__init__(kind, key, f"Invalid {kind} ({key}) revision: {reason}")
