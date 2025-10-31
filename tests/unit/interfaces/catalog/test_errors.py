"""Unit tests for calista.interfaces.catalog.errors."""

from calista.interfaces.catalog import errors

# pylint: disable=magic-value-comparison


class TestCatalogError:
    """Tests for CatalogError."""

    @staticmethod
    def test_catalog_error_message_custom():
        """CatalogError uses the provided message if given."""
        error = errors.CatalogError(
            kind="instrument",
            key="WFPC2",
            message="Custom error message",
        )
        assert str(error) == "Custom error message"

    @staticmethod
    def test_catalog_error_attributes():
        """CatalogError stores the kind and key attributes correctly."""
        error = errors.CatalogError(
            kind="telescope",
            key="HST",
        )
        assert error.kind == "telescope"
        assert error.key == "HST"

    @staticmethod
    def test_catalog_error_message_default():
        """CatalogError uses a default message if none is provided."""
        error = errors.CatalogError(kind="site", key="LDT")
        assert str(error) == "site (LDT) catalog error"


class TestVersionConflictError:
    """Tests for VersionConflictError."""

    @staticmethod
    def test_version_conflict_error_attributes():
        """VersionConflictError stores the kind, key, head, and expected attributes correctly."""
        head = 5
        expected = 4
        error = errors.VersionConflictError(
            kind="telescope",
            key="HST",
            head=head,
            expected=expected,
        )
        assert error.kind == "telescope"
        assert error.key == "HST"
        assert error.head == head
        assert error.expected == expected

    @staticmethod
    def test_version_conflict_error_message():
        """VersionConflictError constructs the correct error message."""
        error = errors.VersionConflictError(
            kind="instrument",
            key="WFPC2",
            head=7,
            expected=5,
        )
        assert str(error) == "instrument (WFPC2) version conflict: head=7, expected=5"


class TestNoChangeError:
    """Tests for NoChangeError."""

    @staticmethod
    def test_no_change_error_message():
        """NoChangeError constructs the correct error message."""
        error = errors.NoChangeError(
            kind="site",
            key="LDT",
        )
        assert str(error) == "site (LDT) revision introduces no changes"

    @staticmethod
    def test_no_change_error_attributes():
        """NoChangeError stores the kind and key attribute correctly."""
        error = errors.NoChangeError(
            kind="site",
            key="LDT",
        )
        assert error.kind == "site"
        assert error.key == "LDT"


class TestInvalidSnapshotError:
    """Tests for InvalidSnapshotError."""

    @staticmethod
    def test_invalid_snapshot_error_message():
        """InvalidSnapshotError constructs the correct error message."""
        error = errors.InvalidSnapshotError(
            kind="site",
            key="LDT",
            reason="missing required field 'name'",
        )
        assert (
            str(error) == "Invalid site (LDT) snapshot: missing required field 'name'"
        )

    @staticmethod
    def test_invalid_snapshot_error_attributes():
        """InvalidSnapshotError stores the kind, key, and reason attribute correctly."""
        reason = "missing required field 'name'"
        error = errors.InvalidSnapshotError(
            kind="site",
            key="LDT",
            reason=reason,
        )
        assert error.reason == reason
        assert error.kind == "site"
        assert error.key == "LDT"


class TestInvalidRevisionError:
    """Tests for InvalidRevisionError."""

    @staticmethod
    def test_invalid_revision_error_message():
        """InvalidRevisionError constructs the correct error message."""
        error = errors.InvalidRevisionError(
            kind="site",
            key="LDT",
            reason="invalid version number",
        )
        assert str(error) == "Invalid site (LDT) revision: invalid version number"

    @staticmethod
    def test_invalid_revision_error_attributes():
        """InvalidRevisionError stores the kind, key, and reason attribute correctly."""
        reason = "invalid version number"
        error = errors.InvalidRevisionError(
            kind="site",
            key="LDT",
            reason=reason,
        )
        assert error.reason == reason
        assert error.kind == "site"
        assert error.key == "LDT"


class TestSiteNotFoundError:
    """Tests for SiteNotFoundError."""

    @staticmethod
    def test_site_not_found_error_message():
        """SiteNotFoundError constructs the correct error message."""
        error = errors.SiteNotFoundError("LDT")
        assert str(error) == "Site (LDT) not found in catalog"

    @staticmethod
    def test_site_not_found_error_attributes():
        """SiteNotFoundError stores the kind and key attribute correctly."""
        error = errors.SiteNotFoundError("LDT")
        assert error.kind == "site"
        assert error.key == "LDT"


class TestTelescopeNotFoundError:
    """Tests for TelescopeNotFoundError."""

    @staticmethod
    def test_telescope_not_found_error_message():
        """TelescopeNotFoundError constructs the correct error message."""
        error = errors.TelescopeNotFoundError("HST")
        assert str(error) == "Telescope (HST) not found in catalog"

    @staticmethod
    def test_telescope_not_found_error_attributes():
        """TelescopeNotFoundError stores the kind and key attribute correctly."""
        error = errors.TelescopeNotFoundError("HST")
        assert error.kind == "telescope"
        assert error.key == "HST"


class TestInstrumentNotFoundError:
    """Tests for InstrumentNotFoundError."""

    @staticmethod
    def test_instrument_not_found_error_attributes():
        """InstrumentNotFoundError stores the kind and key attribute correctly."""
        error = errors.InstrumentNotFoundError("WFPC2")
        assert error.kind == "instrument"
        assert error.key == "WFPC2"

    @staticmethod
    def test_instrument_not_found_error_message():
        """InstrumentNotFoundError constructs the correct error message."""
        error = errors.InstrumentNotFoundError("WFPC2")
        assert str(error) == "Instrument (WFPC2) not found in catalog"


class TestFacilityNotFoundError:
    """Tests for FacilityNotFoundError."""

    @staticmethod
    def test_facility_not_found_error_attributes():
        """FacilityNotFoundError stores the kind and key attribute correctly."""
        error = errors.FacilityNotFoundError("XYZ")
        assert error.kind == "facility"
        assert error.key == "XYZ"

    @staticmethod
    def test_facility_not_found_error_message():
        """FacilityNotFoundError constructs the correct error message."""
        error = errors.FacilityNotFoundError("XYZ")
        assert str(error) == "Facility (XYZ) not found in catalog"


class TestDuplicateFacilityError:
    """Tests for DuplicateFacilityError."""

    @staticmethod
    def test_duplicate_facility_error_attributes():
        """DuplicateFacilityError stores the kind and key attribute correctly."""
        error = errors.DuplicateFacilityError("ABC")
        assert error.kind == "facility"
        assert error.key == "ABC"

    @staticmethod
    def test_duplicate_facility_error_message():
        """DuplicateFacilityError constructs the correct error message."""
        error = errors.DuplicateFacilityError("ABC")
        assert str(error) == "Facility (ABC) already exists in catalog"


class TestInvalidFacilityError:
    """Tests for InvalidFacilityError."""

    @staticmethod
    def test_invalid_facility_error_message():
        """InvalidFacilityError constructs the correct error message."""
        error = errors.InvalidFacilityError(
            key="OBS1",
            reason="references unknown site 'LDT'",
        )
        assert str(error) == "Invalid facility (OBS1): references unknown site 'LDT'"

    @staticmethod
    def test_invalid_facility_error_attributes():
        """InvalidFacilityError stores the kind, key, and reason attribute correctly."""
        reason = "references unknown site 'LDT'"
        error = errors.InvalidFacilityError(
            key="OBS1",
            reason=reason,
        )
        assert error.reason == reason
        assert error.kind == "facility"
        assert error.key == "OBS1"
