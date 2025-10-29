"""Unit tests for the patch_telescope handler in the catalog service layer."""

from __future__ import annotations

import re

import pytest

from calista.interfaces.catalog.errors import (
    InvalidRevisionError,
    TelescopeNotFoundError,
)
from calista.service_layer import commands
from tests.unit.service_layer.handlers.base import HandlerTestBase

# pylint: disable=magic-value-comparison


class TestPatchTelescope(HandlerTestBase):
    """Tests for the patch_telescope handler via the message bus."""

    # Used by BaseHandlerTest to seed the bus with a telescope
    def _seed_bus(self, request):
        """Seed the message bus with a telescope."""
        make_telescope_params = request.getfixturevalue("make_telescope_params")
        self.bus.handle(
            commands.PublishTelescopeRevision(
                **make_telescope_params("T1", "Test Telescope 1")
            )
        )

    def test_commits(self):
        """Handler commits the unit of work."""

        cmd = commands.PatchTelescope(telescope_code="T1", name="Patched Telescope A")
        self.bus.handle(cmd=cmd)

        self.assert_committed()

    def test_publishes_new_revision_on_patch(self):
        """Patching a telescope creates a new revision."""

        patch_cmd = commands.PatchTelescope(
            telescope_code="T1",
            name="Patched Telescope",
            source="Some Source",
            aperture_m=2.0,
        )
        self.bus.handle(cmd=patch_cmd)

        # updated to version 2
        t1 = self.bus.uow.catalogs.telescopes.get("T1")
        assert t1 is not None
        assert t1.version == 2
        assert t1.name == "Patched Telescope"
        assert t1.source == "Some Source"
        assert t1.aperture_m == 2.0

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

    def test_preserves_unpatched_fields(self):
        """Unpatched fields are preserved in the new revision."""

        patch_cmd = commands.PatchTelescope(
            telescope_code="T1",
            name="Patched Telescope",
        )
        self.bus.handle(cmd=patch_cmd)

        # updated to version 2
        t1 = self.bus.uow.catalogs.telescopes.get("T1")
        assert t1 is not None
        assert t1.version == 2
        assert t1.name == "Patched Telescope"

        # unpatched fields preserved
        t1_v1 = self.bus.uow.catalogs.telescopes.get("T1", version=1)
        assert t1_v1 is not None
        assert t1.source == t1_v1.source and t1.source is not None
        assert t1.aperture_m == t1_v1.aperture_m and t1.aperture_m is not None

    def test_can_clear_fields(self):
        """Patching can clear fields by setting them to None."""

        patch_cmd = commands.PatchTelescope(
            telescope_code="T1",
            source=None,
            aperture_m=None,
        )
        self.bus.handle(cmd=patch_cmd)

        # updated to version 2
        t1 = self.bus.uow.catalogs.telescopes.get("T1")
        assert t1 is not None
        assert t1.version == 2
        assert t1.source is None
        assert t1.aperture_m is None

    def test_cannot_clear_name_field(self):
        """Patching cannot clear the name field (raises error)."""

        patch_cmd = commands.PatchTelescope(
            telescope_code="T1",
            name=None,
        )
        with pytest.raises(
            InvalidRevisionError,
            match=re.escape("Invalid telescope (T1) revision: name cannot be cleared"),
        ):
            self.bus.handle(cmd=patch_cmd)
