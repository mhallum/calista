"""Unit tests for the patch_telescope handler in the catalog service layer."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from calista.interfaces.catalog.errors import TelescopeNotFoundError
from calista.service_layer import commands

if TYPE_CHECKING:
    from calista.service_layer.messagebus import MessageBus

# pylint: disable=magic-value-comparison


class TestPatchTelescope:
    """Tests for the patch_telescope handler via the message bus."""

    bus: MessageBus

    @pytest.fixture(autouse=True)
    def _attach_bus(self, make_test_bus, make_telescope_params):
        """Attach a message bus to the test instance and seed with a telescope."""
        self.bus = make_test_bus()  # available in every test method
        self.bus.handle(
            commands.PublishTelescopeRevision(
                **make_telescope_params("T1", "Test Telescope 1")
            )
        )

    def _assert_committed(self):
        assert hasattr(self.bus.uow, "committed")
        assert self.bus.uow.committed is True

    def test_commits(self):
        """Handler commits the unit of work."""

        cmd = commands.PatchTelescope(telescope_code="T1", name="Patched Telescope A")
        self.bus.handle(cmd=cmd)

        self._assert_committed()

    def test_publishes_new_revision_on_patch(self):
        """Patching a telescope creates a new revision."""

        patch_cmd = commands.PatchTelescope(
            telescope_code="T1", name="Patched Telescope"
        )
        self.bus.handle(cmd=patch_cmd)

        # updated to version 2
        t1 = self.bus.uow.catalogs.telescopes.get("T1")
        assert t1 is not None
        assert t1.version == 2
        assert t1.name == "Patched Telescope"

    def test_idempotent_on_no_change(self):
        """Re-patching with no changes does not create a new version."""

        patch_cmd = commands.PatchTelescope(
            telescope_code="T1", name="Test Telescope 1"
        )
        self.bus.handle(cmd=patch_cmd)

        t1 = self.bus.uow.catalogs.telescopes.get("T1")
        assert t1 is not None
        assert t1.version == 1  # still version 1

    def test_raises_on_patch_nonexistent_telescope(self):
        """Patching a non-existent telescope raises TelescopeNotFoundError."""
        cmd = commands.PatchTelescope(telescope_code="NONEXISTENT", name="No Tel")
        with pytest.raises(
            TelescopeNotFoundError,
            match=re.escape("Telescope (NONEXISTENT) not found in catalog"),
        ):
            self.bus.handle(cmd)

    def test_logs_noop_on_no_change(self, caplog):
        """Re-patching with no changes logs a no-op message."""

        cmd = commands.PatchTelescope(telescope_code="T1", name="Test Telescope 1")

        with caplog.at_level("DEBUG"):
            self.bus.handle(cmd=cmd)

        assert any(
            "PatchTelescope T1: no changes; noop" in message
            for message in caplog.messages
        )
