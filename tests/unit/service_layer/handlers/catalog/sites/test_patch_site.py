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

        cmd = commands.PatchSite(
            site_code="A",
            name="Patched Site A",
            timezone="UTC",
            lat_deg=12.34,
            lon_deg=56.78,
            elevation_m=1000,
            mpc_code="123",
        )
        self.bus.handle(cmd)

        # updated to version 2
        site = self.bus.uow.catalogs.sites.get("A")
        assert site is not None
        assert site.version == 2
        assert site.name == "Patched Site A"
        assert site.timezone == "UTC"
        assert site.lat_deg == 12.34
        assert site.lon_deg == 56.78
        assert site.elevation_m == 1000
        assert site.mpc_code == "123"

    def test_preserves_unpatched_fields(self):
        """Patching a site preserves unpatched fields."""

        cmd = commands.PatchSite(
            site_code="A",
            name="Patched Site A",
        )
        self.bus.handle(cmd)

        # updated to version 2
        site = self.bus.uow.catalogs.sites.get("A")
        assert site is not None
        assert site.version == 2
        assert site.name == "Patched Site A"

        # unpatched fields preserved
        site_v1 = self.bus.uow.catalogs.sites.get("A", version=1)
        assert site_v1 is not None
        assert site.source == site_v1.source and site.source is not None
        assert site.timezone == site_v1.timezone and site.timezone is not None
        assert site.lat_deg == site_v1.lat_deg and site.lat_deg is not None
        assert site.lon_deg == site_v1.lon_deg and site.lon_deg is not None
        assert site.elevation_m == site_v1.elevation_m and site.elevation_m is not None
        assert site.mpc_code == site_v1.mpc_code and site.mpc_code is not None

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

    def test_can_clear_fields(self):
        """Patching can clear optional fields by setting them to None."""

        # First patch to set optional fields
        cmd_set = commands.PatchSite(
            site_code="A",
            source="Source X",
            timezone="UTC",
            lat_deg=12.34,
            lon_deg=56.78,
            elevation_m=1000,
            mpc_code="123",
        )
        self.bus.handle(cmd_set)

        site = self.bus.uow.catalogs.sites.get("A")
        assert site is not None
        assert site.source == "Source X"
        assert site.timezone == "UTC"
        assert site.lat_deg == 12.34
        assert site.lon_deg == 56.78
        assert site.elevation_m == 1000
        assert site.mpc_code == "123"

        # Now patch to clear those fields
        cmd_clear = commands.PatchSite(
            site_code="A",
            source=None,
            timezone=None,
            lat_deg=None,
            lon_deg=None,
            elevation_m=None,
            mpc_code=None,
        )
        self.bus.handle(cmd_clear)

        site_cleared = self.bus.uow.catalogs.sites.get("A")
        assert site_cleared is not None
        assert site_cleared.source is None
        assert site_cleared.timezone is None
        assert site_cleared.lat_deg is None
        assert site_cleared.lon_deg is None
        assert site_cleared.elevation_m is None
        assert site_cleared.mpc_code is None
        assert site_cleared.version == 3  # now version 3
