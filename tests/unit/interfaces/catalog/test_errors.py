"""Unit tests for calista.interfaces.catalog.errors."""

from calista.interfaces.catalog.errors import (
    CatalogError,
    FacilityNotFoundError,
    InvalidSnapshotError,
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


def test_invalid_snapshot_error_message():
    """InvalidSnapshotError constructs the correct error message."""
    error = InvalidSnapshotError(
        kind="site",
        key="LDT",
        reason="missing required field 'name'",
    )
    assert str(error) == "Invalid site (LDT) snapshot: missing required field 'name'"


def test_facility_not_found_error_message():
    """FacilityNotFoundError constructs the correct error message."""
    error = FacilityNotFoundError("XYZ")
    assert str(error) == "Facility (XYZ) not found in catalog"
