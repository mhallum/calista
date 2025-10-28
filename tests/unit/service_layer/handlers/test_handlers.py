"""Unit tests for handlers."""

import re

import pytest

from calista.interfaces.catalog.errors import SiteNotFoundError, TelescopeNotFoundError
from calista.service_layer import commands

from .fakes import bootstrap_test_bus

# pylint: disable=consider-using-assignment-expr
# pylint: disable=magic-value-comparison


class TestPublishSiteRevision:
    """Tests for the publish_site_revision handler via the message bus."""

    @staticmethod
    def test_commits(make_site_params):
        """Handler commits the unit of work."""
        bus = bootstrap_test_bus()
        cmd = commands.PublishSiteRevision(**make_site_params("A", "Test Site A"))
        bus.handle(cmd)
        assert bus.uow.committed is True

    @staticmethod
    def test_publishes_new_revision(make_site_params):
        """Publishes a new site revision to the catalog."""
        bus = bootstrap_test_bus()
        cmd = commands.PublishSiteRevision(**make_site_params("A", "Test Site A"))
        bus.handle(cmd)
        site = bus.uow.catalogs.sites.get("A")
        assert site is not None
        assert site.version == 1
        assert site.name == "Test Site A"

    @staticmethod
    def test_idempotent_on_no_change(make_site_params):
        """Re-publishing the same revision does not create a new version."""
        bus = bootstrap_test_bus()
        cmd = commands.PublishSiteRevision(**make_site_params("A", "Test Site A"))
        bus.handle(cmd)
        bus.handle(cmd)
        assert bus.uow.catalogs.sites.get("A").version == 1  # still version 1

    @staticmethod
    def test_publishes_new_revision_on_change(make_site_params):
        """Publishing a changed revision creates a new version."""
        bus = bootstrap_test_bus()
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


class TestPatchSite:
    """Tests for the patch_site handler via the message bus."""

    @staticmethod
    def test_commits(make_site_params):
        """Handler commits the unit of work."""
        bus = bootstrap_test_bus()
        # First publish a site to patch
        publish_cmd = commands.PublishSiteRevision(
            **make_site_params("A", "Test Site A")
        )
        bus.handle(publish_cmd)

        patch_cmd = commands.PatchSite(site_code="A", name="Patched Site A")
        bus.handle(patch_cmd)
        assert bus.uow.committed is True

    @staticmethod
    def test_publishes_new_revision_on_patch(make_site_params):
        """Patching a site creates a new revision."""
        bus = bootstrap_test_bus()
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
    def test_idempotent_on_no_change(make_site_params):
        """Re-patching with no changes does not create a new version."""
        bus = bootstrap_test_bus()
        # First publish a site to patch
        publish_cmd = commands.PublishSiteRevision(
            **make_site_params("A", "Test Site A")
        )
        bus.handle(publish_cmd)

        patch_cmd = commands.PatchSite(site_code="A", name="Test Site A")
        bus.handle(patch_cmd)
        assert bus.uow.catalogs.sites.get("A").version == 1  # still version 1

    @staticmethod
    def test_raises_on_patch_nonexistent_site():
        """Patching a non-existent site raises SiteNotFoundError."""
        bus = bootstrap_test_bus()
        patch_cmd = commands.PatchSite(site_code="NONEXISTENT", name="No Site")
        with pytest.raises(
            SiteNotFoundError,
            match=re.escape("Site (NONEXISTENT) not found in catalog"),
        ):
            bus.handle(patch_cmd)


class TestPublishTelescopeRevision:
    """Tests for the publish_telescope_revision handler via the message bus."""

    @staticmethod
    def test_commits(make_telescope_params):
        """Handler commits the unit of work."""
        bus = bootstrap_test_bus()

        cmd = commands.PublishTelescopeRevision(
            **make_telescope_params("T1", "Test Telescope 1")
        )
        bus.handle(cmd)
        assert bus.uow.committed is True

    @staticmethod
    def test_publishes_new_revision(make_telescope_params):
        """Publishes a new telescope to the catalog."""
        bus = bootstrap_test_bus()

        cmd = commands.PublishTelescopeRevision(
            **make_telescope_params("T1", "Test Telescope 1")
        )
        bus.handle(cmd)

        telescope = bus.uow.catalogs.telescopes.get("T1")
        assert telescope is not None
        assert telescope.version == 1
        assert telescope.name == "Test Telescope 1"

    @staticmethod
    def test_idempotent_on_no_change(make_telescope_params):
        """Re-publishing the same telescope revision does not create a new version."""
        bus = bootstrap_test_bus()

        cmd = commands.PublishTelescopeRevision(
            **make_telescope_params("T1", "Test Telescope 1")
        )
        bus.handle(cmd)
        bus.handle(cmd)
        assert bus.uow.catalogs.telescopes.get("T1").version == 1  # still version 1

    @staticmethod
    def test_logs_noop_on_no_change(make_telescope_params, caplog):
        """Re-publishing the same telescope revision logs a no-op message."""
        bus = bootstrap_test_bus()

        cmd = commands.PublishTelescopeRevision(
            **make_telescope_params("T1", "Test Telescope 1")
        )
        bus.handle(cmd)

        with caplog.at_level("DEBUG"):
            bus.handle(cmd)
            assert any(
                "PublishTelescopeRevision T1: no changes; noop" in message
                for message in caplog.messages
            )

    @staticmethod
    def test_publishes_new_revision_on_change(make_telescope_params):
        """Publishing a changed telescope revision creates a new version."""
        bus = bootstrap_test_bus()

        cmd1 = commands.PublishTelescopeRevision(
            **make_telescope_params("T1", "Test Telescope 1")
        )
        bus.handle(cmd1)

        cmd2 = commands.PublishTelescopeRevision(
            **make_telescope_params("T1", "Test Telescope 1 v2")
        )
        bus.handle(cmd2)

        # updated to version 2
        assert bus.uow.catalogs.telescopes.get("T1").version == 2
        assert bus.uow.catalogs.telescopes.get("T1").name == "Test Telescope 1 v2"

        # first version still exists
        assert (
            bus.uow.catalogs.telescopes.get("T1", version=1).name == "Test Telescope 1"
        )
        assert bus.uow.catalogs.telescopes.get("T1", version=1).version == 1


class TestPatchTelescope:
    """Tests for the patch_telescope handler via the message bus."""

    def _seed_telescope(self, bus, make_telescope_params, **telescope_params):
        """Helper to seed a telescope for the patch tests."""
        publish_cmd = commands.PublishTelescopeRevision(
            **make_telescope_params(**telescope_params)
        )
        bus.handle(publish_cmd)

    def test_commits(self, make_telescope_params):
        """Handler commits the unit of work."""
        bus = bootstrap_test_bus()

        # seed a telescope to patch first
        self._seed_telescope(
            bus,
            make_telescope_params,
            telescope_code="T1",
            name="Test Telescope 1",
        )

        cmd = commands.PatchTelescope(telescope_code="T1", name="Patched Telescope A")
        bus.handle(cmd=cmd)

        assert bus.uow.committed is True

    def test_publishes_new_revision_on_patch(self, make_telescope_params):
        """Patching a telescope creates a new revision."""
        bus = bootstrap_test_bus()

        # seed a telescope first
        self._seed_telescope(
            bus,
            make_telescope_params,
            telescope_code="T1",
            name="Test Telescope 1",
        )

        patch_cmd = commands.PatchTelescope(
            telescope_code="T1", name="Patched Telescope"
        )
        bus.handle(cmd=patch_cmd)

        # updated to version 2
        assert bus.uow.catalogs.telescopes.get("T1").version == 2
        assert bus.uow.catalogs.telescopes.get("T1").name == "Patched Telescope"

    def test_idempotent_on_no_change(self, make_telescope_params):
        """Re-patching with no changes does not create a new version."""
        bus = bootstrap_test_bus()

        # seed a telescope first
        self._seed_telescope(
            bus,
            make_telescope_params,
            telescope_code="T1",
            name="Test Telescope 1",
        )

        patch_cmd = commands.PatchTelescope(
            telescope_code="T1", name="Test Telescope 1"
        )
        bus.handle(cmd=patch_cmd)

        assert bus.uow.catalogs.telescopes.get("T1").version == 1  # still version 1

    def test_raises_on_patch_nonexistent_telescope(self):
        """Patching a non-existent telescope raises TelescopeNotFoundError."""
        bus = bootstrap_test_bus()
        patch_cmd = commands.PatchTelescope(telescope_code="NONEXISTENT", name="No Tel")
        with pytest.raises(
            TelescopeNotFoundError,
            match=re.escape("Telescope (NONEXISTENT) not found in catalog"),
        ):
            bus.handle(patch_cmd)

    def test_logs_noop_on_no_change(self, make_telescope_params, caplog):
        """Re-patching with no changes logs a no-op message."""
        bus = bootstrap_test_bus()

        # seed a telescope first
        self._seed_telescope(
            bus, make_telescope_params, telescope_code="T1", name="Test Telescope 1"
        )

        patch_cmd = commands.PatchTelescope(
            telescope_code="T1", name="Test Telescope 1"
        )

        with caplog.at_level("DEBUG"):
            bus.handle(cmd=patch_cmd)
            assert any(
                "PatchTelescope T1: no changes; noop" in message
                for message in caplog.messages
            )
