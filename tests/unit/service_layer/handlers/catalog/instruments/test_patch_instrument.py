"""Tests for the patch_instrument handler"""

import re

import pytest

from calista.interfaces.catalog import errors as catalog_errors
from calista.service_layer import commands
from tests.unit.service_layer.handlers.base import HandlerTestBase

# pylint: disable=magic-value-comparison


class TestPatchInstrument(HandlerTestBase):
    """Tests for the patch_instrument handler via the message bus."""

    # --- Setup ----

    # Used by BaseHandlerTest
    def _seed_bus(self, request):
        """Seed the bus with an initial instrument revision."""
        make_instrument_params = request.getfixturevalue("make_instrument_params")
        cmd = commands.PublishInstrumentRevision(
            **make_instrument_params("I1", "Test Instrument 1")
        )
        self.bus.handle(cmd)

    # --- Tests ----

    def test_commits(self):
        """Handler commits the unit of work."""

        cmd = commands.PatchInstrument(
            instrument_code="I1", name="Patched Instrument 1"
        )
        self.bus.handle(cmd=cmd)

        self.assert_committed()

    def test_publishes_new_revision_on_patch(self):
        """Patching a instrument creates a new revision."""

        cmd = commands.PatchInstrument(instrument_code="I1", name="Patched Instrument")
        self.bus.handle(cmd=cmd)

        # updated to version 2
        i1 = self.bus.uow.catalogs.instruments.get("I1")
        assert i1 is not None
        assert i1.version == 2
        assert i1.name == "Patched Instrument"

    def test_idempotent_on_no_change(self):
        """Re-patching with no changes does not create a new version."""

        cmd = commands.PatchInstrument(instrument_code="I1", name="Test Instrument 1")
        self.bus.handle(cmd=cmd)

        i1 = self.bus.uow.catalogs.instruments.get("I1")
        assert i1 is not None
        assert i1.name == "Test Instrument 1"
        assert i1.version == 1  # still version 1

    def test_raises_on_patch_nonexistent_instrument(self):
        """Patching a non-existent instrument raises InstrumentNotFoundError."""

        cmd = commands.PatchInstrument(
            instrument_code="NONEXISTENT", name="No Instrument"
        )
        with pytest.raises(
            catalog_errors.InstrumentNotFoundError,
            match=re.escape("Instrument (NONEXISTENT) not found in catalog"),
        ):
            self.bus.handle(cmd)

    def test_logs_on_no_change(self, caplog):
        """Re-patching with no changes logs a no-op message."""

        cmd = commands.PatchInstrument(instrument_code="I1", name="Test Instrument 1")

        with caplog.at_level("DEBUG"):
            self.bus.handle(cmd=cmd)

        assert any(
            "PatchInstrument I1: no changes; noop" in message
            for message in caplog.messages
        )

    def test_unpatched_fields_preserved(self):
        """Unpatched fields are preserved in the new revision."""

        # First, patch only the name
        cmd = commands.PatchInstrument(instrument_code="I1", name="Patched Instrument")
        self.bus.handle(cmd)

        # updated to version 2
        i1 = self.bus.uow.catalogs.instruments.get("I1")
        assert i1 is not None
        assert i1.version == 2
        assert i1.name == "Patched Instrument"

        # unpatched fields preserved
        i1_v1 = self.bus.uow.catalogs.instruments.get("I1", version=1)
        assert i1_v1 is not None
        assert i1.source == i1_v1.source and i1.source is not None
        assert i1.mode == i1_v1.mode and i1.mode is not None

    def test_can_clear_source_and_mode(self):
        """Can clear optional fields source and mode via patching."""

        # First, patch to set source and mode
        cmd = commands.PatchInstrument(
            instrument_code="I1", source="Initial Source", mode="Initial Mode"
        )
        self.bus.handle(cmd)

        # updated to version 2
        i1 = self.bus.uow.catalogs.instruments.get("I1")
        assert i1 is not None
        assert i1.version == 2
        assert i1.source == "Initial Source"
        assert i1.mode == "Initial Mode"

        # Now, patch to clear source and mode
        cmd = commands.PatchInstrument(instrument_code="I1", source=None, mode=None)
        self.bus.handle(cmd)

        # updated to version 3
        i1 = self.bus.uow.catalogs.instruments.get("I1")
        assert i1 is not None
        assert i1.version == 3
        assert i1.source is None
        assert i1.mode is None

    def test_cannot_clear_name(self):
        """Patching to clear the name field raises an error."""

        cmd = commands.PatchInstrument(instrument_code="I1", name=None)
        with pytest.raises(
            catalog_errors.InvalidRevisionError,
            match=re.escape("Invalid instrument (I1) revision: name cannot be cleared"),
        ):
            self.bus.handle(cmd)
