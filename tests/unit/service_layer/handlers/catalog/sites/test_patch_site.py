"""Unit tests for the patch_site handler in the catalog service layer."""

import re

import pytest

from calista.interfaces.catalog import errors as catalog_errors
from calista.service_layer import commands


class TestPatchSite:
    """Tests for the patch_site handler via the message bus."""

    @staticmethod
    def test_commits(make_test_bus, make_site_params):
        """Handler commits the unit of work."""
        bus = make_test_bus()
        # First publish a site to patch
        publish_cmd = commands.PublishSiteRevision(
            **make_site_params("A", "Test Site A")
        )
        bus.handle(publish_cmd)

        patch_cmd = commands.PatchSite(site_code="A", name="Patched Site A")
        bus.handle(patch_cmd)
        assert bus.uow.committed is True

    @staticmethod
    def test_publishes_new_revision_on_patch(make_test_bus, make_site_params):
        """Patching a site creates a new revision."""
        bus = make_test_bus()
        # First publish a site to patch
        publish_cmd = commands.PublishSiteRevision(
            **make_site_params("A", "Test Site A")
        )
        bus.handle(publish_cmd)

        patch_cmd = commands.PatchSite(site_code="A", name="Patched Site A")
        bus.handle(patch_cmd)

        # updated to version 2
        assert bus.uow.catalogs.sites.get("A").version == 2
        assert bus.uow.catalogs.sites.get("A").name == "Patched Site A"

    @staticmethod
    def test_idempotent_on_no_change(make_test_bus, make_site_params):
        """Re-patching with no changes does not create a new version."""
        bus = make_test_bus()
        # First publish a site to patch
        publish_cmd = commands.PublishSiteRevision(
            **make_site_params("A", "Test Site A")
        )
        bus.handle(publish_cmd)

        patch_cmd = commands.PatchSite(site_code="A", name="Test Site A")
        bus.handle(patch_cmd)
        assert bus.uow.catalogs.sites.get("A").version == 1  # still version 1

    @staticmethod
    def test_raises_on_patch_nonexistent_site(make_test_bus):
        """Patching a non-existent site raises SiteNotFoundError."""
        bus = make_test_bus()
        patch_cmd = commands.PatchSite(site_code="NONEXISTENT", name="No Site")
        with pytest.raises(
            catalog_errors.SiteNotFoundError,
            match=re.escape("Site (NONEXISTENT) not found in catalog"),
        ):
            bus.handle(patch_cmd)
