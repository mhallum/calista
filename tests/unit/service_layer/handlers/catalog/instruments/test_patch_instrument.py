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
            message == "PatchInstrument I1: no changes; noop"
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

    def test_cannot_clear_name(self):
        """Patching to clear the name field raises an error."""

        cmd = commands.PatchInstrument(instrument_code="I1", name=None)
        with pytest.raises(
            catalog_errors.InvalidRevisionError,
            match=re.escape("Invalid instrument (I1) revision: name cannot be cleared"),
        ):
            self.bus.handle(cmd)

    @pytest.mark.parametrize(
        "field", ["source", "mode"], ids=lambda field: f"can_clear_{field}"
    )
    def test_can_clear_clearable_fields(self, field):
        """Patching can clear fields (those clearable) by setting them to None.

        clearable fields: source, mode
        """

        # make sure the field is initially set
        seeded_instrument = self.bus.uow.catalogs.instruments.get("I1")
        assert getattr(seeded_instrument, field) is not None

        # Issue patch command
        patch_cmd = commands.PatchInstrument(instrument_code="I1", **{field: None})
        self.bus.handle(cmd=patch_cmd)

        # check that field is cleared in new head revision
        patched_instrument = self.bus.uow.catalogs.instruments.get("I1")
        assert patched_instrument is not None
        assert getattr(patched_instrument, field) is None

    def test_comment_field_does_not_inherit(self):
        """The comment field does not inherit from head if not patched."""

        # First patch with a comment
        first_patch_cmd = commands.PatchInstrument(
            instrument_code="I1",
            comment="First patch comment",
        )
        self.bus.handle(cmd=first_patch_cmd)

        i1_v2 = self.bus.uow.catalogs.instruments.get("I1")
        assert i1_v2 is not None
        assert i1_v2.version == 2
        assert i1_v2.comment == "First patch comment"

        # Second patch without a comment
        second_patch_cmd = commands.PatchInstrument(
            instrument_code="I1",
            name="Second Patch Name",
        )
        self.bus.handle(cmd=second_patch_cmd)

        i1_v3 = self.bus.uow.catalogs.instruments.get("I1")
        assert i1_v3 is not None
        assert i1_v3.version == 3
        assert i1_v3.name == "Second Patch Name"
        assert i1_v3.comment is None  # comment does not inherit
