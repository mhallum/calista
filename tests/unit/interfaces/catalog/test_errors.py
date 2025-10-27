"""Unit tests for calista.interfaces.catalog.errors."""

from calista.interfaces.catalog.errors import (
    CatalogError,
    NoChangeError,
    VersionConflictError,
)

# pylint: disable=magic-value-comparison


def test_catalog_error_message_default():
    """CatalogError uses a default message if none is provided."""
    error = CatalogError(kind="site", key="LDT")
    assert str(error) == "site (LDT) catalog error"


def test_version_conflict_error_message():
    """VersionConflictError constructs the correct error message."""
    error = VersionConflictError(
        kind="site",
        key="LDT",
        head=3,
        expected=2,
    )
    assert str(error) == "site (LDT) version conflict: head=3, expected=2"


def test_no_change_error_message():
    """NoChangeError constructs the correct error message."""
    error = NoChangeError(
        kind="site",
        key="LDT",
    )
    assert str(error) == "site (LDT) revision introduces no changes"
