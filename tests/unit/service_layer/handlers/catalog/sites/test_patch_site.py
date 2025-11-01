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

    def test_logs_on_no_change(self, caplog):
        """Patching with no changes logs a debug message."""

        cmd = commands.PatchSite(site_code="A", name="Site A")
        self.bus.handle(cmd)

        with caplog.at_level("DEBUG"):
            self.bus.handle(cmd)

        # Check that a debug message about no-op was logged
        debug_messages = [
            record.message for record in caplog.records if record.levelname == "DEBUG"
        ]
        assert any(msg == "PatchSite A: no changes; noop" for msg in debug_messages)

    def test_raises_on_patch_nonexistent_site(self):
        """Patching a non-existent site raises SiteNotFoundError."""

        cmd = commands.PatchSite(site_code="NONEXISTENT", name="No Site")
        with pytest.raises(
            catalog_errors.SiteNotFoundError,
            match=re.escape("Site (NONEXISTENT) not found in catalog"),
        ):
            self.bus.handle(cmd)

    @pytest.mark.parametrize(
        "field",
        ["source", "lat_deg", "lon_deg", "elevation_m", "mpc_code"],
        ids=lambda field: f"can_clear_{field}",
    )
    def test_can_clear_clearable_fields(self, field):
        """Patching can clear fields (those clearable) by setting them to None.

        clearable fields: source, lat_deg, lon_deg, elevation_m, mpc_code
        """

        # make sure the field is initially set
        seeded_site = self.bus.uow.catalogs.sites.get("A")
        assert seeded_site is not None
        assert getattr(seeded_site, field) is not None

        # Issue patch command
        patch_cmd = commands.PatchSite(site_code="A", **{field: None})
        self.bus.handle(cmd=patch_cmd)

        # check that field is cleared in new head revision
        patched_site = self.bus.uow.catalogs.sites.get("A")
        assert patched_site is not None
        assert getattr(patched_site, field) is None

    def test_cannot_clear_name_field(self):
        """The name field cannot be cleared (raises error)."""

        patch_cmd = commands.PatchSite(
            site_code="A",
            name=None,
        )
        with pytest.raises(
            catalog_errors.InvalidRevisionError,
            match=re.escape("Invalid site (A) revision: name cannot be cleared"),
        ):
            self.bus.handle(cmd=patch_cmd)

    def test_comment_field_does_not_inherit(self):
        """The comment field does not inherit from head if not patched."""

        # First patch with a comment
        first_patch_cmd = commands.PatchSite(
            site_code="A",
            comment="First patch comment",
        )
        self.bus.handle(cmd=first_patch_cmd)

        site_v2 = self.bus.uow.catalogs.sites.get("A")
        assert site_v2 is not None
        assert site_v2.version == 2
        assert site_v2.comment == "First patch comment"

        # Second patch without a comment
        second_patch_cmd = commands.PatchSite(
            site_code="A",
            name="Second Patch Name",
        )
        self.bus.handle(cmd=second_patch_cmd)

        site_v3 = self.bus.uow.catalogs.sites.get("A")
        assert site_v3 is not None
        assert site_v3.version == 3
        assert site_v3.name == "Second Patch Name"
        assert site_v3.comment is None  # comment does not inherit
