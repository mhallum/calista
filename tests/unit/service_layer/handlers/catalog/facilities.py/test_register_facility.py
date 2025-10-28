"""Tests for the register_facility handler"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from calista.interfaces.catalog import errors as catalog_errors
from calista.service_layer import commands

if TYPE_CHECKING:
    from calista.service_layer.messagebus import MessageBus


class TestRegisterFacility:
    """Tests for the register_facility handler via the message bus."""

    bus: MessageBus

    @pytest.fixture(autouse=True)
    def _attach_bus(
        self,
        make_test_bus,
        make_site_params,
        make_telescope_params,
        make_instrument_params,
    ):
        """Attach a message bus to the test instance and seed with a site, telescope, and instrument."""
        self.bus = make_test_bus()  # available in every test method
        # Seed with a site
        self.bus.handle(
            commands.PublishSiteRevision(**make_site_params("S1", "Test Site 1"))
        )
        # Seed with a telescope
        self.bus.handle(
            commands.PublishTelescopeRevision(
                **make_telescope_params("T1", "Test Telescope 1")
            )
        )
        # Seed with an instrument
        self.bus.handle(
            commands.PublishInstrumentRevision(
                **make_instrument_params("I1", "Test Instrument 1")
            )
        )

        self._reset_committed()

    def _assert_committed(self):
        assert hasattr(self.bus.uow, "committed")
        assert self.bus.uow.committed is True, "Expected UoW to be committed"

    def _assert_not_committed(self):
        assert hasattr(self.bus.uow, "committed")
        assert self.bus.uow.committed is False, "Expected UoW to not be committed"

    def _reset_committed(self):
        if hasattr(self.bus.uow, "committed"):
            self.bus.uow.committed = False

    def test_commits(self):
        """Handler commits the unit of work."""

        cmd = commands.RegisterFacility(
            facility_code="S1/T1/I1",
            site_code="S1",
            telescope_code="T1",
            instrument_code="I1",
        )
        self.bus.handle(cmd)
        self._assert_committed()

    def test_registers_new_facility(self):
        """Registers a new facility in the catalog."""

        cmd = commands.RegisterFacility(
            facility_code="S1/T1/I1",
            site_code="S1",
            telescope_code="T1",
            instrument_code="I1",
        )
        self.bus.handle(cmd)

        facility = self.bus.uow.catalogs.facilities.get("S1/T1/I1")
        assert facility is not None
        assert facility.facility_code == "S1/T1/I1"
        assert facility.site_code == "S1"
        assert facility.telescope_code == "T1"
        assert facility.instrument_code == "I1"

    def test_raises_on_duplicate_facility(self):
        """Registering a facility with an existing code raises DuplicateFacilityError."""

        # first registration
        cmd = commands.RegisterFacility(
            facility_code="S1/T1/I1",
            site_code="S1",
            telescope_code="T1",
            instrument_code="I1",
        )
        self.bus.handle(cmd)  # first registration

        # registration with same code again (but different components)
        cmd = commands.RegisterFacility(
            facility_code="S1/T1/I1",
            site_code="S2",
            telescope_code="T2",
            instrument_code="I2",
        )

        with pytest.raises(
            catalog_errors.DuplicateFacilityError,
            match=re.escape("Facility (S1/T1/I1) already exists in catalog"),
        ):
            self.bus.handle(cmd)  # duplicate registration

    def test_raises_on_invalid_site(self):
        """Registering a facility with an unknown site raises InvalidFacilityError."""

        cmd = commands.RegisterFacility(
            facility_code="UNKNOWN/T1/I1",
            site_code="UNKNOWN",
            telescope_code="T1",
            instrument_code="I1",
        )

        with pytest.raises(
            catalog_errors.InvalidFacilityError,
            match=re.escape(
                "Invalid facility (UNKNOWN/T1/I1): unknown site code: UNKNOWN"
            ),
        ):
            self.bus.handle(cmd)  # registration with invalid site

    def test_raises_on_invalid_telescope(self):
        """Registering a facility with an unknown telescope raises InvalidFacilityError."""

        cmd = commands.RegisterFacility(
            facility_code="S1/UNKNOWN/I1",
            site_code="S1",
            telescope_code="UNKNOWN",
            instrument_code="I1",
        )

        with pytest.raises(
            catalog_errors.InvalidFacilityError,
            match=re.escape(
                "Invalid facility (S1/UNKNOWN/I1): unknown telescope code: UNKNOWN"
            ),
        ):
            self.bus.handle(cmd)  # registration with invalid telescope

    def test_raises_on_invalid_instrument(self):
        """Registering a facility with an unknown instrument raises InvalidFacilityError."""

        cmd = commands.RegisterFacility(
            facility_code="S1/T1/UNKNOWN",
            site_code="S1",
            telescope_code="T1",
            instrument_code="UNKNOWN",
        )

        with pytest.raises(
            catalog_errors.InvalidFacilityError,
            match=re.escape(
                "Invalid facility (S1/T1/UNKNOWN): unknown instrument code: UNKNOWN"
            ),
        ):
            self.bus.handle(cmd)  # registration with invalid instrument

    def test_idempotent_register(self):
        """Re-registering the same facility code is idempotent."""
        self._assert_not_committed()

        cmd = commands.RegisterFacility(
            facility_code="S1/T1/I1",
            site_code="S1",
            telescope_code="T1",
            instrument_code="I1",
        )
        self.bus.handle(cmd)
        self._reset_committed()
        self.bus.handle(cmd)  # second time should be a noop
        self._assert_not_committed()
