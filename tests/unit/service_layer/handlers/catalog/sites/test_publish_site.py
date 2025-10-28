"""Unit tests for the publish_site_revision handler."""

from calista.service_layer import commands

# pylint: disable=magic-value-comparison


def test_commits(make_test_bus, make_site_params):
    """Handler commits the unit of work."""
    bus = make_test_bus()
    cmd = commands.PublishSiteRevision(**make_site_params("A", "Test Site A"))
    bus.handle(cmd)
    assert bus.uow.committed is True


def test_publishes_new_revision(make_test_bus, make_site_params):
    """Publishes a new site revision to the catalog."""
    bus = make_test_bus()
    cmd = commands.PublishSiteRevision(**make_site_params("A", "Test Site A"))
    bus.handle(cmd)
    site = bus.uow.catalogs.sites.get("A")
    assert site is not None
    assert site.version == 1
    assert site.name == "Test Site A"


def test_idempotent_on_no_change(make_test_bus, make_site_params):
    """Re-publishing the same revision does not create a new version."""
    bus = make_test_bus()
    cmd = commands.PublishSiteRevision(**make_site_params("A", "Test Site A"))
    bus.handle(cmd)
    bus.handle(cmd)
    assert bus.uow.catalogs.sites.get("A").version == 1  # still version 1


def test_publishes_new_revision_on_change(make_test_bus, make_site_params):
    """Publishing a changed revision creates a new version."""
    bus = make_test_bus()
    cmd1 = commands.PublishSiteRevision(**make_site_params("A", "Test Site A"))
    bus.handle(cmd1)
    cmd2 = commands.PublishSiteRevision(**make_site_params("A", "Test Site A v2"))
    bus.handle(cmd2)

    # updated to version 2
    assert bus.uow.catalogs.sites.get("A").version == 2
    assert bus.uow.catalogs.sites.get("A").name == "Test Site A v2"

    # first version still exists
    assert bus.uow.catalogs.sites.get("A", version=1).name == "Test Site A"
    assert bus.uow.catalogs.sites.get("A", version=1).version == 1
