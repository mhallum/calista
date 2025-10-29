"""Unit tests for the patch_site handler in the catalog service layer."""

import re

import pytest

from calista.interfaces.catalog import errors as catalog_errors
from calista.service_layer import commands
from tests.unit.service_layer.handlers.base import HandlerTestBase

# pylint: disable=magic-value-comparison


class TestPatchSite(HandlerTestBase):
    """Tests for the patch_site handler via the message bus."""

    # --- Setup ---

    # Used by HandlerTestBase to seed the bus
    def _seed_bus(self, request) -> None:
        """Seed the bus with any fixtures declared in seed_uses."""
        make_site_params = request.getfixturevalue("make_site_params")
        self.bus.handle(
            cmd=commands.PublishSiteRevision(**make_site_params("A", "Site A"))
        )

    # --- Tests ---

    def test_commits(self):
        """Handler commits the unit of work."""

        cmd = commands.PatchSite(site_code="A", name="Patched Site A")
        self.bus.handle(cmd)
        self.assert_committed()

    def test_publishes_new_revision_on_patch(self):
        """Patching a site creates a new revision."""

        cmd = commands.PatchSite(site_code="A", name="Patched Site A")
        self.bus.handle(cmd)

        # updated to version 2
        site = self.bus.uow.catalogs.sites.get("A")
        assert site is not None
        assert site.version == 2
        assert site.name == "Patched Site A"

    def test_idempotent_on_no_change(self):
        """Patching with no changes does not create a new version."""

        cmd = commands.PatchSite(site_code="A", name="Site A")
        self.bus.handle(cmd)

        site = self.bus.uow.catalogs.sites.get("A")
        assert site is not None
        assert site.name == "Site A"
        assert site.version == 1  # still version 1

        self.assert_not_committed()

    def test_raises_on_patch_nonexistent_site(self):
        """Patching a non-existent site raises SiteNotFoundError."""

        cmd = commands.PatchSite(site_code="NONEXISTENT", name="No Site")
        with pytest.raises(
            catalog_errors.SiteNotFoundError,
            match=re.escape("Site (NONEXISTENT) not found in catalog"),
        ):
            self.bus.handle(cmd)
