"""In-memory FacilityCatalog adapter implementation."""

from calista.adapters.catalog.memory_store import InMemoryCatalogData
from calista.interfaces.catalog.errors import (
    DuplicateFacilityError,
    InvalidFacilityError,
)
from calista.interfaces.catalog.facility_catalog import Facility, FacilityCatalog

# pylint: disable=consider-using-assignment-expr


class InMemoryFacilityCatalog(FacilityCatalog):
    """In-memory implementation of the FacilityCatalog interface."""

    def __init__(self, data: InMemoryCatalogData):
        self._data = data

    def get(self, facility_code: str) -> Facility | None:
        facility = self._data.facilities.get(facility_code.upper(), None)
        return facility

    def register(self, facility: Facility) -> None:
        facility_code = facility.facility_code.upper()
        if facility_code in self._data.facilities:
            raise DuplicateFacilityError(facility_code)

        # Validate referenced site, telescope, and instrument exist
        if facility.site_code not in self._data.sites:
            raise InvalidFacilityError(
                facility_code,
                f"unknown site code: {facility.site_code}",
            )
        if facility.telescope_code not in self._data.telescopes:
            raise InvalidFacilityError(
                facility_code,
                f"unknown telescope code: {facility.telescope_code}",
            )
        if facility.instrument_code not in self._data.instruments:
            raise InvalidFacilityError(
                facility_code,
                f"unknown instrument code: {facility.instrument_code}",
            )

        self._data.facilities[facility_code] = facility
