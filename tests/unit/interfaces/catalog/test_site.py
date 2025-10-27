"""Unit tests for site catalog interfaces."""

from datetime import datetime, timezone

import pytest

from calista.interfaces.catalog.errors import InvalidRevisionError, InvalidSnapshotError
from calista.interfaces.catalog.site_catalog import (
    SitePatch,
    SiteRevision,
    SiteSnapshot,
)

# pylint: disable=magic-value-comparison,too-few-public-methods


class TestSiteSnapshotValidation:
    """Tests for site snapshot validation errors."""

    @staticmethod
    @pytest.mark.parametrize("lat", [-91, 91])
    def test_invalid_latitude(lat):
        """Test invalid latitude values raises InvalidSnapshotError."""
        with pytest.raises(
            InvalidSnapshotError, match="lat_deg must be between -90 and 90 degrees"
        ):
            SiteSnapshot(
                site_code="A",
                version=1,
                name="Test Site A",
                recorded_at=datetime.now(tz=timezone.utc),
                lat_deg=lat,
            )

    @staticmethod
    @pytest.mark.parametrize("lon", [-181, 181])
    def test_invalid_longitude(lon):
        """Test invalid longitude values raises InvalidSnapshotError."""
        with pytest.raises(
            InvalidSnapshotError, match="lon_deg must be between -180 and 180 degrees"
        ):
            SiteSnapshot(
                site_code="A",
                version=1,
                name="Test Site A",
                recorded_at=datetime.now(tz=timezone.utc),
                lon_deg=lon,
            )

    @staticmethod
    @pytest.mark.parametrize("mpc_code", ["12", "1234", "1@3"])
    def test_invalid_mpc_code(mpc_code):
        """Test invalid MPC codes raises InvalidSnapshotError."""
        with pytest.raises(
            InvalidSnapshotError,
            match="mpc_code must be a 3-character alphanumeric string if set",
        ):
            SiteSnapshot(
                site_code="A",
                version=1,
                name="Test Site A",
                recorded_at=datetime.now(tz=timezone.utc),
                mpc_code=mpc_code,
            )

    @staticmethod
    def test_non_utc_recorded_at():
        """Test non-UTC recorded_at raises InvalidSnapshotError."""
        non_utc_dt = datetime.now()  # naive datetime, not UTC
        with pytest.raises(
            InvalidSnapshotError, match="recorded_at must be timezone-aware UTC"
        ):
            SiteSnapshot(
                site_code="A",
                version=1,
                name="Test Site A",
                recorded_at=non_utc_dt,
            )

    @staticmethod
    def test_valid_snapshot():
        """Test a valid site snapshot passes validation."""
        snapshot = SiteSnapshot(
            site_code="A",
            version=1,
            name="Test Site A",
            recorded_at=datetime.now(tz=timezone.utc),
            lat_deg=45.0,
            lon_deg=-120.0,
            mpc_code="ABC",
        )
        # pylint: disable=magic-value-comparison
        assert snapshot.site_code == "A"
        assert snapshot.version == 1
        assert snapshot.name == "Test Site A"
        assert snapshot.lat_deg == 45.0
        assert snapshot.lon_deg == -120.0
        assert snapshot.mpc_code == "ABC"


class TestSiteRevisionValidation:
    """Tests for site revision validation errors."""

    @staticmethod
    @pytest.mark.parametrize("lat", [-91, 91])
    def test_invalid_latitude(lat):
        """Test invalid latitude values raises InvalidRevisionError."""
        with pytest.raises(
            InvalidRevisionError, match="lat_deg must be between -90 and 90 degrees"
        ):
            SiteRevision(
                site_code="A",
                name="Test Site A",
                lat_deg=lat,
            )

    @staticmethod
    @pytest.mark.parametrize("lon", [-181, 181])
    def test_invalid_longitude(lon):
        """Test invalid longitude values raises InvalidRevisionError."""
        with pytest.raises(
            InvalidRevisionError, match="lon_deg must be between -180 and 180 degrees"
        ):
            SiteRevision(
                site_code="A",
                name="Test Site A",
                lon_deg=lon,
            )

    @staticmethod
    @pytest.mark.parametrize("mpc_code", ["12", "1234", "1@3"])
    def test_invalid_mpc_code(mpc_code):
        """Test invalid MPC codes raises InvalidRevisionError."""
        with pytest.raises(
            InvalidRevisionError,
            match="mpc_code must be a 3-character alphanumeric string if set",
        ):
            SiteRevision(
                site_code="A",
                name="Test Site A",
                mpc_code=mpc_code,
            )

    @staticmethod
    def test_valid_revision():
        """Test a valid site revision passes validation."""
        revision = SiteRevision(
            site_code="A",
            name="Test Site A",
            lat_deg=45.0,
            lon_deg=-120.0,
            mpc_code="ABC",
        )
        # pylint: disable=magic-value-comparison
        assert revision.site_code == "A"
        assert revision.name == "Test Site A"
        assert revision.lat_deg == 45.0
        assert revision.lon_deg == -120.0
        assert revision.mpc_code == "ABC"


class TestSiteCodeNormalization:
    """Tests for site code normalization to uppercase."""

    @staticmethod
    def test_snapshot_site_code_normalization():
        """SiteSnapshot site_code is normalized to uppercase."""
        snapshot = SiteSnapshot(
            site_code="abc",
            version=1,
            name="Test Site ABC",
            recorded_at=datetime.now(tz=timezone.utc),
        )
        assert snapshot.site_code == "ABC"

    @staticmethod
    def test_revision_site_code_normalization():
        """SiteRevision site_code is normalized to uppercase."""
        revision = SiteRevision(
            site_code="def",
            name="Test Site DEF",
        )
        assert revision.site_code == "DEF"


class TestSiteRevisionDiff:
    """Tests for SiteRevision.get_diff method."""

    @staticmethod
    def test_no_diff():
        """get_diff returns None when there are no changes."""
        head = SiteSnapshot(
            site_code="A",
            version=1,
            name="Test Site A",
            recorded_at=datetime.now(tz=timezone.utc),
            lat_deg=45.0,
        )
        revision = SiteRevision(
            site_code="A",
            name="Test Site A",
            lat_deg=45.0,
        )
        diff = revision.get_diff(head)
        assert diff is None

    @staticmethod
    def test_with_diff():
        """get_diff returns correct diff when there are changes."""
        head = SiteSnapshot(
            site_code="A",
            version=1,
            name="Test Site A",
            recorded_at=datetime.now(tz=timezone.utc),
            lat_deg=45.0,
            lon_deg=-120.0,
        )
        revision = SiteRevision(
            site_code="A",
            name="Updated Site A",
            lat_deg=46.0,
            lon_deg=-120.0,
        )
        diff = revision.get_diff(head)
        expected_diff = {
            "name": ("Test Site A", "Updated Site A"),
            "lat_deg": (45.0, 46.0),
        }
        assert diff == expected_diff

    @staticmethod
    def test_diff_with_different_site_codes():
        """get_diff raises InvalidRevisionError when site_codes differ."""
        head = SiteSnapshot(
            site_code="A",
            version=1,
            name="Test Site A",
            recorded_at=datetime.now(tz=timezone.utc),
        )
        revision = SiteRevision(
            site_code="B",
            name="Test Site B",
        )
        with pytest.raises(
            InvalidRevisionError,
            match="site_code mismatch with head \\(A\\)",
        ):
            revision.get_diff(head)


class TestApplySitePatch:
    """Tests for SitePatch.apply_to method."""

    @staticmethod
    def test_apply_patch():
        """Applying a patch updates only specified fields."""
        head = SiteSnapshot(
            site_code="A",
            version=1,
            name="Test Site A",
            recorded_at=datetime.now(tz=timezone.utc),
            lat_deg=45.0,
            lon_deg=-120.0,
        )
        patch = SitePatch(
            name="Patched Site A",
            lat_deg=46.0,
        )
        revised = patch.apply_to(head)
        assert revised.site_code == "A"
        assert revised.name == "Patched Site A"
        assert revised.lat_deg == 46.0
        assert revised.lon_deg == -120.0  # unchanged
