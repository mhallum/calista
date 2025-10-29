"""Unit tests for the publish_site_revision handler."""

from calista.service_layer import commands
from tests.unit.service_layer.handlers.base import HandlerTestBase

# pylint: disable=magic-value-comparison


class TestPublishSiteRevision(HandlerTestBase):
    """Tests for the publish_site_revision handler via the message bus."""

    def test_commits(self, make_site_params):
        """Handler commits the unit of work."""
        cmd = commands.PublishSiteRevision(**make_site_params("A", "Test Site A"))
        self.bus.handle(cmd)
        self.assert_committed()

    def test_publishes_new_revision(self, make_site_params):
        """Publishes a new site revision to the catalog."""

        cmd = commands.PublishSiteRevision(
            **make_site_params(
                "A",
                "Test Site A",
                source="Source X",
                timezone="UTC",
                lat_deg=12.34,
                lon_deg=56.78,
                elevation_m=1000,
                mpc_code="123",
            )
        )
        self.bus.handle(cmd)
        site = self.bus.uow.catalogs.sites.get("A")
        assert site is not None
        assert site.version == 1
        assert site.name == "Test Site A"
        assert site.source == "Source X"
        assert site.timezone == "UTC"
        assert site.lat_deg == 12.34
        assert site.lon_deg == 56.78
        assert site.elevation_m == 1000
        assert site.mpc_code == "123"

    def test_idempotent_on_no_change(self, make_site_params):
        """Re-publishing the same revision does not create a new version."""
        cmd = commands.PublishSiteRevision(**make_site_params("A", "Test Site A"))
        self.bus.handle(cmd)
        self.bus.handle(cmd)

        site = self.bus.uow.catalogs.sites.get("A")
        assert site is not None
        assert site.name == "Test Site A"
        assert site.version == 1  # still version 1

    def test_logs_on_no_change(self, make_site_params, caplog):
        """Re-publishing the same revision logs a debug message."""
        cmd = commands.PublishSiteRevision(**make_site_params("A", "Test Site A"))
        self.bus.handle(cmd)

        with caplog.at_level("DEBUG"):
            self.bus.handle(cmd)

        # Check that a debug message about no-op was logged
        debug_messages = [
            record.message for record in caplog.records if record.levelname == "DEBUG"
        ]
        assert any(
            msg == "PublishSiteRevision A: no changes; noop" for msg in debug_messages
        )

    def test_publishes_new_revision_on_change(self, make_site_params):
        """Publishing a changed revision creates a new version."""
        cmd1 = commands.PublishSiteRevision(**make_site_params("A", "Test Site A"))
        self.bus.handle(cmd1)
        cmd2 = commands.PublishSiteRevision(**make_site_params("A", "Test Site A v2"))
        self.bus.handle(cmd2)

        # updated to version 2
        site_head = self.bus.uow.catalogs.sites.get("A")
        assert site_head is not None
        assert site_head.version == 2
        assert site_head.name == "Test Site A v2"

        # first version still exists
        site_v1 = self.bus.uow.catalogs.sites.get("A", version=1)
        assert site_v1 is not None
        assert site_v1.name == "Test Site A"
        assert site_v1.version == 1
