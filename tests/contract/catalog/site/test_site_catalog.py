"""Contract tests for SiteCatalog adapters.

These tests ensure adapters can publish revisions and retrieve snapshots, maintain
deterministic site versions, accept case-insensitive codes, raise the expected catalog
errors, and persist recorded_at timestamps as timezone-aware UTC datetimes.
"""

from datetime import timedelta

import pytest

from calista.interfaces.catalog.errors import NoChangeError, VersionConflictError
from calista.interfaces.catalog.site_catalog import SiteRevision, SiteSnapshot

# pylint: disable=magic-value-comparison


def test_can_publish_and_retrieve_site(catalog, make_site_params):
    """A site revision can be published and then retrieved as a snapshot."""
    site_rev = SiteRevision(**make_site_params(site_code="TEST", name="Test Site"))
    catalog.publish(site_rev, expected_version=0)
    site_snapshot = catalog.get(site_code="TEST")

    assert isinstance(site_snapshot, SiteSnapshot)
    assert not site_rev.get_diff(site_snapshot)
    assert site_snapshot.version == 1


def test_head_version_updates_on_publish(catalog, make_site_params):
    """The head version updates correctly after publishing revisions."""

    assert catalog.get_head_version(site_code="TEST") is None

    site_rev1 = SiteRevision(**make_site_params(site_code="TEST", name="Test Site"))
    catalog.publish(site_rev1, expected_version=0)
    assert catalog.get_head_version(site_code="TEST") == 1

    site_rev2 = SiteRevision(
        **make_site_params(site_code="TEST", name="Updated Test Site")
    )
    catalog.publish(site_rev2, expected_version=1)
    assert catalog.get_head_version(site_code="TEST") == 2


def test_get_specific_version(catalog, make_site_params):
    """A specific version of a site can be retrieved."""
    site_rev1 = SiteRevision(**make_site_params(site_code="TEST", name="Test Site"))
    catalog.publish(site_rev1, expected_version=0)

    site_rev2 = SiteRevision(
        **make_site_params(site_code="TEST", name="Updated Test Site")
    )
    catalog.publish(site_rev2, expected_version=1)

    snapshot_v1 = catalog.get(site_code="TEST", version=1)
    snapshot_v2 = catalog.get(site_code="TEST", version=2)

    assert snapshot_v1 is not None
    assert snapshot_v1.name == "Test Site"
    assert snapshot_v1.version == 1

    assert snapshot_v2 is not None
    assert snapshot_v2.name == "Updated Test Site"
    assert snapshot_v2.version == 2


def test_get_returns_head_version_by_default(catalog, make_site_params):
    """Getting a site without specifying version returns the head version."""
    site_rev1 = SiteRevision(**make_site_params(site_code="TEST", name="Test Site"))
    catalog.publish(site_rev1, expected_version=0)

    site_rev2 = SiteRevision(
        **make_site_params(site_code="TEST", name="Updated Test Site")
    )
    catalog.publish(site_rev2, expected_version=1)

    site_snapshot = catalog.get(site_code="TEST")

    assert site_snapshot is not None
    assert site_snapshot.name == "Updated Test Site"
    assert site_snapshot.version == 2


def test_get_head_version_returns_none_for_nonexistent_site(catalog):
    """Getting the head version of a nonexistent site returns None."""
    assert catalog.get_head_version(site_code="NONEXISTENT") is None


def test_cannot_publish_with_version_conflict(catalog, make_site_params):
    """Publishing a site revision with an unexpected version raises VersionConflictError."""
    site_rev1 = SiteRevision(**make_site_params(site_code="TEST", name="Test Site"))
    catalog.publish(site_rev1, expected_version=0)

    site_rev2 = SiteRevision(
        **make_site_params(site_code="TEST", name="Updated Test Site")
    )

    with pytest.raises(VersionConflictError) as exc_info:
        catalog.publish(site_rev2, expected_version=0)  # should be 1

    err = exc_info.value
    assert err.kind == "site"
    assert err.key == "TEST"
    assert err.head == 1
    assert err.expected == 0


def test_return_none_for_nonexistent_site(catalog):
    """Getting a nonexistent site returns None."""
    site_snapshot = catalog.get(site_code="NONEXISTENT")
    assert site_snapshot is None


@pytest.mark.parametrize(
    "code", ["TESTSITE", "testsite", "testSite"], ids=["upper", "lower", "mixed"]
)
def test_get_is_case_insensitive(code, catalog, make_site_params):
    """Getting a site by code is case-insensitive."""
    site_rev = SiteRevision(**make_site_params(site_code="TestSite", name="Test Site"))
    catalog.publish(site_rev, expected_version=0)

    site_snapshot = catalog.get(site_code=code)
    assert site_snapshot is not None
    assert site_snapshot.site_code == "TESTSITE"


def test_publish_no_change_raises_error(catalog, make_site_params):
    """Publishing an identical site revision raises NoChangeError."""

    # First, publish an initial revision
    site_rev = SiteRevision(**make_site_params(site_code="TEST", name="Test Site"))
    catalog.publish(site_rev, expected_version=0)

    # Attempt to publish the another revision with the same data
    site_rev = SiteRevision(**make_site_params(site_code="TEST", name="Test Site"))
    with pytest.raises(NoChangeError) as exc_info:
        catalog.publish(site_rev, expected_version=1)

    # Assert that the exception stored the proper attributes
    error = exc_info.value
    assert error.kind == "site"
    assert error.key == "TEST"

    # Verify that the head version remains unchanged
    assert catalog.get_head_version(site_code="TEST") == 1


def test_get_nonexistent_version_returns_none(catalog, make_site_params):
    """Getting a specific nonexistent version returns None."""
    site_rev = SiteRevision(**make_site_params(site_code="TEST", name="Test Site"))
    catalog.publish(site_rev, expected_version=0)

    assert catalog.get(site_code="TEST", version=99) is None


def test_publish_sets_recorded_at_utc(catalog, make_site_params):
    """Publishing a revision stores recorded_at in UTC."""
    site_rev = SiteRevision(**make_site_params(site_code="TEST", name="Test Site"))
    catalog.publish(site_rev, expected_version=0)

    snapshot = catalog.get(site_code="TEST")
    assert snapshot is not None
    assert snapshot.recorded_at.tzinfo is not None
    assert snapshot.recorded_at.utcoffset() == timedelta(0)


def test_versions_are_tracked_per_site(catalog, make_site_params):
    """Site versions advance independently per site code."""
    rev_a1 = SiteRevision(**make_site_params(site_code="ALPHA", name="Alpha 1"))
    catalog.publish(rev_a1, expected_version=0)

    rev_b1 = SiteRevision(**make_site_params(site_code="BETA", name="Beta 1"))
    catalog.publish(rev_b1, expected_version=0)

    rev_a2 = SiteRevision(**make_site_params(site_code="ALPHA", name="Alpha 2"))
    catalog.publish(rev_a2, expected_version=1)

    assert catalog.get_head_version(site_code="ALPHA") == 2
    assert catalog.get_head_version(site_code="BETA") == 1

    assert catalog.get(site_code="BETA", version=1).name == "Beta 1"
