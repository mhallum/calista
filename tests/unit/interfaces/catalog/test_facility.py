"""Unit tests for facility catalog data models."""

from calista.interfaces.catalog.facility_catalog import Facility

# pylint: disable=too-few-public-methods
# pylint: disable=magic-value-comparison


class TestFacilityCodeNormalization:
    """Tests for Facility code normalization."""

    @staticmethod
    def test_code_normalization():
        """Facility codes are normalized to uppercase."""
        facility = Facility(
            facility_code="ldt/deveny",
            site_code="ldt",
            telescope_code="deveny",
            instrument_code="imager",
        )
        assert facility.facility_code == "LDT/DEVENY"
        assert facility.site_code == "LDT"
        assert facility.telescope_code == "DEVENY"
        assert facility.instrument_code == "IMAGER"
