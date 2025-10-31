from datetime import timedelta

import pytest

from calista.interfaces.catalog.errors import NoChangeError, VersionConflictError


def test_can_publish_and_retrieve_revision(catalog, make_params):
    """A revision can be published and then retrieved as a snapshot."""
    revision = catalog.REVISION_CLASS(**make_params("A", name="Test A"))

    catalog.publish(revision, expected_version=0)
    snapshot = catalog.get("A")

    assert isinstance(snapshot, catalog.SNAPSHOT_CLASS)
    assert not revision.get_diff(snapshot)
    assert snapshot.version == 1


def test_head_version_updates_on_publish(catalog, make_params):
    """The head version updates correctly after publishing revisions."""

    assert catalog.get_head_version("A") is None

    rev1 = catalog.REVISION_CLASS(**make_params("A", name="Test A"))
    catalog.publish(rev1, expected_version=0)
    assert catalog.get_head_version("A") == 1

    rev2 = catalog.REVISION_CLASS(**make_params("A", name="Updated Test A"))
    catalog.publish(rev2, expected_version=1)
    assert catalog.get_head_version("A") == 2


def test_get_specific_version(catalog, make_params):
    """A specific version of a catalog entry can be retrieved."""
    rev1 = catalog.REVISION_CLASS(**make_params("A", name="Test A"))
    catalog.publish(rev1, expected_version=0)

    rev2 = catalog.REVISION_CLASS(**make_params("A", name="Updated Test A"))
    catalog.publish(rev2, expected_version=1)

    snapshot_v1 = catalog.get("A", version=1)
    snapshot_v2 = catalog.get("A", version=2)

    assert snapshot_v1 is not None
    assert snapshot_v1.name == "Test A"
    assert snapshot_v1.version == 1

    assert snapshot_v2 is not None
    assert snapshot_v2.name == "Updated Test A"
    assert snapshot_v2.version == 2


def test_get_returns_head_version_by_default(catalog, make_params):
    """Getting a catalog entry without specifying version returns the head version."""
    rev1 = catalog.REVISION_CLASS(**make_params("A", name="Test A"))
    catalog.publish(rev1, expected_version=0)

    rev2 = catalog.REVISION_CLASS(**make_params("A", name="Updated Test A"))
    catalog.publish(rev2, expected_version=1)

    snapshot = catalog.get("A")

    assert snapshot is not None
    assert snapshot.name == "Updated Test A"
    assert snapshot.version == 2


def test_get_head_version_returns_none_for_nonexistent_entry(catalog):
    """Getting the head version of a nonexistent catalog entry returns None."""
    assert catalog.get_head_version("NONEXISTENT") is None


def test_cannot_publish_with_version_conflict(catalog, make_params):
    """Publishing a site revision with an unexpected version raises VersionConflictError."""
    rev1 = catalog.REVISION_CLASS(**make_params("A", name="Test A"))
    catalog.publish(rev1, expected_version=0)

    rev2 = catalog.REVISION_CLASS(**make_params("A", name="Updated Test A"))

    with pytest.raises(VersionConflictError) as exc_info:
        catalog.publish(rev2, expected_version=0)  # should be 1

    err = exc_info.value
    assert err.kind == catalog.KIND
    assert err.key == "A"
    assert err.head == 1
    assert err.expected == 0


def test_return_none_for_nonexistent_code(catalog):
    """Getting a nonexistent catalog code returns None."""
    snapshot = catalog.get("NONEXISTENT")
    assert snapshot is None


@pytest.mark.parametrize(
    "code", ["TEST", "test", "teSt"], ids=["upper", "lower", "mixed"]
)
def test_get_is_case_insensitive(code, catalog, make_params):
    """Getting a site by code is case-insensitive."""
    rev = catalog.REVISION_CLASS(**make_params("test", name="Test"))
    catalog.publish(rev, expected_version=0)

    snapshot = catalog.get(code)
    assert snapshot is not None
    assert getattr(snapshot, catalog.CODE_ATTR) == "TEST"


def test_publish_no_change_raises_error(catalog, make_params):
    """Publishing an identical catalog revision raises NoChangeError."""

    # First, publish an initial revision
    rev = catalog.REVISION_CLASS(**make_params("A", name="Test A"))
    catalog.publish(rev, expected_version=0)

    # Attempt to publish the another revision with the same data
    rev = catalog.REVISION_CLASS(**make_params("A", name="Test A"))
    with pytest.raises(NoChangeError) as exc_info:
        catalog.publish(rev, expected_version=1)

    # Assert that the exception stored the proper attributes
    error = exc_info.value
    assert error.kind == catalog.KIND
    assert error.key == "A"

    # Verify that the head version remains unchanged
    assert catalog.get_head_version("A") == 1


def test_get_nonexistent_version_returns_none(catalog, make_params):
    """Getting a specific nonexistent version returns None."""
    rev = catalog.REVISION_CLASS(**make_params("A", name="Test A"))
    catalog.publish(rev, expected_version=0)

    assert catalog.get("A", version=99) is None


def test_publish_sets_recorded_at_utc(catalog, make_params):
    """Publishing a revision stores recorded_at in UTC."""
    rev = catalog.REVISION_CLASS(**make_params("A", name="Test A"))
    catalog.publish(rev, expected_version=0)

    snapshot = catalog.get("A")
    assert snapshot is not None
    assert snapshot.recorded_at.tzinfo is not None
    assert snapshot.recorded_at.utcoffset() == timedelta(0)


def test_versions_are_tracked_per_catalog_code(catalog, make_params):
    """Versions advance independently per catalog code."""
    rev_a1 = catalog.REVISION_CLASS(**make_params("ALPHA", name="Alpha 1"))
    catalog.publish(rev_a1, expected_version=0)

    rev_b1 = catalog.REVISION_CLASS(**make_params("BETA", name="Beta 1"))
    catalog.publish(rev_b1, expected_version=0)

    rev_a2 = catalog.REVISION_CLASS(**make_params("ALPHA", name="Alpha 2"))
    catalog.publish(rev_a2, expected_version=1)

    assert catalog.get_head_version("ALPHA") == 2
    assert catalog.get_head_version("BETA") == 1

    assert catalog.get("BETA", version=1).name == "Beta 1"
