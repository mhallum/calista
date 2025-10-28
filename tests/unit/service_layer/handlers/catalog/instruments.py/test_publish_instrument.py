"""Tests for the publish_instrument_revision handler"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from calista.service_layer import commands

if TYPE_CHECKING:
    from calista.service_layer.messagebus import MessageBus

# pylint: disable=magic-value-comparison


class TestPublishInstrumentRevision:
    """Tests for the publish_instrument_revision handler via the message bus."""

    bus: MessageBus

    @pytest.fixture(autouse=True)
    def _attach_bus(self, make_test_bus):
        """Attach a message bus to the test instance"""
        self.bus = make_test_bus()  # available in every test method

    def _assert_committed(self):
        assert hasattr(self.bus.uow, "committed")
        assert self.bus.uow.committed is True

    def test_commits(self, make_instrument_params):
        """Handler commits the unit of work."""
        cmd = commands.PublishInstrumentRevision(
            **make_instrument_params("I1", "Test Instrument 1")
        )
        self.bus.handle(cmd)
        self._assert_committed()

    def test_publishes_new_revision(self, make_instrument_params):
        """Publishes a new instrument revision to the catalog."""
        cmd = commands.PublishInstrumentRevision(
            **make_instrument_params("I1", "Test Instrument 1")
        )
        self.bus.handle(cmd)
        instrument = self.bus.uow.catalogs.instruments.get("I1")
        assert instrument is not None
        assert instrument.version == 1
        assert instrument.name == "Test Instrument 1"

    def test_idempotent_on_no_change(self, make_instrument_params):
        """Re-publishing the same revision does not create a new version."""
        cmd = commands.PublishInstrumentRevision(
            **make_instrument_params("I1", "Test Instrument 1")
        )
        self.bus.handle(cmd)
        self.bus.handle(cmd)
        i1 = self.bus.uow.catalogs.instruments.get("I1")
        assert i1 is not None
        assert i1.name == "Test Instrument 1"
        assert i1.version == 1  # still version 1

    def test_publishes_new_revision_on_change(self, make_instrument_params):
        """Publishing a changed revision creates a new version."""

        # seed the first revision
        self.bus.handle(
            commands.PublishInstrumentRevision(
                **make_instrument_params("I1", "Test Instrument 1")
            )
        )

        # publish an updated revision
        cmd = commands.PublishInstrumentRevision(
            **make_instrument_params("I1", "Test Instrument 1 v2")
        )
        self.bus.handle(cmd)

        # updated to version 2
        i1_head = self.bus.uow.catalogs.instruments.get("I1")
        assert i1_head is not None
        assert i1_head.version == 2
        assert i1_head.name == "Test Instrument 1 v2"

        # first version still exists
        i1_v1 = self.bus.uow.catalogs.instruments.get("I1", version=1)
        assert i1_v1 is not None
        assert i1_v1.name == "Test Instrument 1"
        assert i1_v1.version == 1
