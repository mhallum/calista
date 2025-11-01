"""Tests for the publish_telescope_revision handler via the message bus."""

from __future__ import annotations

from calista.service_layer import commands
from tests.unit.service_layer.handlers.base import HandlerTestBase

# pylint: disable=magic-value-comparison


class TestPublishTelescopeRevision(HandlerTestBase):
    """Tests for the publish_telescope_revision handler via the message bus."""

    def test_commits(self, make_telescope_params):
        """Test that the UoW is committed after publishing a telescope revision."""
        cmd = commands.PublishTelescopeRevision(
            **make_telescope_params("T1", "Test Telescope 1")
        )
        self.bus.handle(cmd)
        self.assert_committed()

    def test_publishes_new_revision(self, make_telescope_params):
        """Test that a new telescope is published."""
        cmd = commands.PublishTelescopeRevision(
            **make_telescope_params("T1", "Test Telescope 1")
        )
        self.bus.handle(cmd)
        telescope = self.bus.uow.catalogs.telescopes.get("T1")
        assert telescope is not None, "Expected telescope T1 to be published"
        assert telescope.version == 1, "Expected telescope T1 to be at version 1"

    def test_published_data_persists_correctly(self, make_telescope_params):
        """Test that the published telescope data persists correctly."""
        cmd = commands.PublishTelescopeRevision(
            **make_telescope_params(
                "T1",
                "Test Telescope 1",
                source="Some Source",
                aperture_m=2.5,
                comment="Initial publish",
            )
        )
        self.bus.handle(cmd)
        telescope = self.bus.uow.catalogs.telescopes.get("T1")
        assert telescope is not None, "Expected telescope T1 to be published"
        assert telescope.name == "Test Telescope 1", "name did not persist correctly"
        assert telescope.source == "Some Source", "source did not persist correctly"
        assert telescope.aperture_m == 2.5, "aperture_m did not persist correctly"
        assert telescope.comment == "Initial publish", (
            "comment did not persist correctly"
        )

    def test_idempotent_on_no_change(self, make_telescope_params):
        """Test that publishing the same telescope data is idempotent."""
        cmd = commands.PublishTelescopeRevision(
            **make_telescope_params("T1", "Test Telescope 1")
        )
        self.bus.handle(cmd)
        self.bus.handle(cmd)
        t1 = self.bus.uow.catalogs.telescopes.get("T1")
        assert t1 is not None
        assert t1.version == 1

    def test_logs_on_no_change(self, make_telescope_params, caplog):
        """Test that a messaged is logged when publishing the same telescope data."""
        cmd = commands.PublishTelescopeRevision(
            **make_telescope_params("T1", "Test Telescope 1")
        )
        self.bus.handle(cmd)
        with caplog.at_level("DEBUG"):
            self.bus.handle(cmd)
        assert any(
            m == "PublishTelescopeRevision T1: no changes; noop"
            for m in caplog.messages
        )

    def test_publishes_new_revision_on_change(self, make_telescope_params):
        """Test that a new telescope revision is published when data changes."""
        self.bus.handle(
            commands.PublishTelescopeRevision(
                **make_telescope_params("T1", "Test Telescope 1")
            )
        )

        self.bus.handle(
            commands.PublishTelescopeRevision(
                **make_telescope_params("T1", "Test Telescope 1 v2")
            )
        )

        t1_head = self.bus.uow.catalogs.telescopes.get("T1")
        assert t1_head is not None
        assert t1_head.version == 2
        assert t1_head.name == "Test Telescope 1 v2"

        t1_v1 = self.bus.uow.catalogs.telescopes.get("T1", version=1)
        assert t1_v1 is not None
        assert t1_v1.name == "Test Telescope 1"
