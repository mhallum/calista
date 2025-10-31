"""Contract tests for FacilityCatalog implementations."""

import pytest

from calista.interfaces.catalog import errors
from calista.interfaces.catalog.facility_catalog import Facility

# pylint: disable=magic-value-comparison


def test_can_register_and_retrieve_facility(catalog):
    """Test that a facility can be registered and then retrieved."""
    facility = Facility(
        facility_code="TEL/INST",
        site_code="SITE",
        telescope_code="TEL",
        instrument_code="INST",
    )
    catalog.register(facility)
    stored_facility = catalog.get("TEL/INST")
    assert stored_facility is not None
    assert stored_facility == facility


def test_register_duplicate_facility_raises_error(catalog):
    """Test that registering a duplicate facility raises an error."""
    facility = Facility(
        facility_code="TEL/INST",
        site_code="SITE",
        telescope_code="TEL",
        instrument_code="INST",
    )
    catalog.register(facility)

    with pytest.raises(errors.DuplicateFacilityError) as excinfo:
        catalog.register(facility)

    error = excinfo.value
    assert error.kind == "facility"
    assert error.key == "TEL/INST"


def test_register_facility_with_unknown_site_raises_error(catalog):
    """Test that registering a facility with an unknown site code raises an error."""
    facility = Facility(
        facility_code="TEL/INST",
        site_code="UNKNOWN",
        telescope_code="TEL",
        instrument_code="INST",
    )

    with pytest.raises(errors.InvalidFacilityError) as excinfo:
        catalog.register(facility)

    error = excinfo.value
    assert error.kind == "facility"
    assert error.reason == "unknown site code: UNKNOWN"


def test_register_facility_with_unknown_telescope_raises_error(catalog):
    """Test that registering a facility with an unknown telescope code raises an error."""
    facility = Facility(
        facility_code="TEL/INST",
        site_code="SITE",
        telescope_code="UNKNOWN",
        instrument_code="INST",
    )

    with pytest.raises(errors.InvalidFacilityError) as excinfo:
        catalog.register(facility)

    error = excinfo.value
    assert error.kind == "facility"
    assert error.reason == "unknown telescope code: UNKNOWN"


def test_register_facility_with_unknown_instrument_raises_error(catalog):
    """Test that registering a facility with an unknown instrument code raises an error."""
    facility = Facility(
        facility_code="TEL/INST",
        site_code="SITE",
        telescope_code="TEL",
        instrument_code="UNKNOWN",
    )

    with pytest.raises(errors.InvalidFacilityError) as excinfo:
        catalog.register(facility)

    error = excinfo.value
    assert error.kind == "facility"
    assert error.reason == "unknown instrument code: UNKNOWN"


def test_get_nonexistent_facility_returns_none(catalog):
    """Test that getting a nonexistent facility returns None."""
    facility = catalog.get("NONEXISTENT")
    assert facility is None


def test_can_register_and_retrieve_multiple_facilities(catalog):
    """Test that multiple facilities can be registered and retrieved."""
    facility1 = Facility(
        facility_code="TEL1/INST1",
        site_code="SITE",
        telescope_code="TEL",
        instrument_code="INST",
    )
    facility2 = Facility(
        facility_code="TEL2/INST2",
        site_code="SITE",
        telescope_code="TEL",
        instrument_code="INST",
    )
    catalog.register(facility1)
    catalog.register(facility2)

    stored_facility1 = catalog.get("TEL1/INST1")
    stored_facility2 = catalog.get("TEL2/INST2")

    assert stored_facility1 is not None
    assert stored_facility1 == facility1
    assert stored_facility2 is not None
    assert stored_facility2 == facility2


def test_facility_code_case_insensitivity(catalog):
    """Test that facility codes are case-insensitive."""
    facility = Facility(
        facility_code="Tel/Inst",
        site_code="SITE",
        telescope_code="TEL",
        instrument_code="INST",
    )
    catalog.register(facility)
    stored_facility = catalog.get("tel/inst")
    assert stored_facility is not None
    assert stored_facility == facility


def test_register_facility_with_lowercase_codes(catalog):
    """Test that facility codes are normalized to uppercase on registration."""
    facility = Facility(
        facility_code="tel/inst",
        site_code="site",
        telescope_code="tel",
        instrument_code="inst",
    )
    catalog.register(facility)
    stored_facility = catalog.get("TEL/INST")
    assert stored_facility is not None
    assert stored_facility == facility
