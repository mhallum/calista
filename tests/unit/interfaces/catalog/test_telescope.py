"""Unit tests for telescope catalog interfaces."""

from datetime import datetime, timezone

import pytest

from calista.interfaces.catalog import errors as catalog_errors
from calista.interfaces.catalog.telescope_catalog import (
    TelescopePatch,
    TelescopeRevision,
    TelescopeSnapshot,
)

# pylint: disable=magic-value-comparison,too-few-public-methods


class TestTelescopeSnapshotValidation:
    """Tests for telescope snapshot validation."""

    @staticmethod
    def test_invalid_aperture():
        """TelescopeSnapshot raises InvalidSnapshotError for negative aperture."""

        with pytest.raises(catalog_errors.InvalidSnapshotError):
            TelescopeSnapshot(
                telescope_code="TEST",
                version=1,
                name="Test Telescope",
                recorded_at=datetime.now(tz=timezone.utc),
                aperture_m=-1.0,
            )

    @staticmethod
    def test_non_utc_recorded_at():
        """Test non-UTC recorded_at raises InvalidSnapshotError."""
        non_utc_dt = datetime.now()  # naive datetime, not UTC
        with pytest.raises(
            catalog_errors.InvalidSnapshotError,
            match="recorded_at must be timezone-aware UTC",
        ):
            TelescopeSnapshot(
                telescope_code="A",
                version=1,
                name="Test Telescope A",
                recorded_at=non_utc_dt,
            )

    @staticmethod
    def test_valid_snapshot():
        """Test a valid telescope snapshot passes validation."""
        snapshot = TelescopeSnapshot(
            telescope_code="TEST",
            version=1,
            name="Test Telescope",
            recorded_at=datetime.now(tz=timezone.utc),
            aperture_m=2.0,
        )
        assert snapshot.telescope_code == "TEST"
        assert snapshot.aperture_m == 2.0


class TestTelescopeRevisionValidation:
    """Tests for telescope revision validation errors."""

    @staticmethod
    def test_invalid_aperture():
        """TelescopeRevision raises InvalidRevisionError for negative aperture."""

        with pytest.raises(catalog_errors.InvalidRevisionError):
            TelescopeRevision(
                telescope_code="TEST",
                name="Test Telescope",
                aperture_m=-1.0,
            )

    @staticmethod
    def test_valid_revision():
        """Test a valid telescope revision passes validation."""
        revision = TelescopeRevision(
            telescope_code="TEST",
            name="Test Telescope",
            aperture_m=2.0,
        )
        assert revision.telescope_code == "TEST"
        assert revision.aperture_m == 2.0


class TestTelescopeCodeNormalization:
    """Tests for telescope code normalization to uppercase."""

    @staticmethod
    def test_snapshot_code_normalization():
        """TelescopeSnapshot normalizes telescope_code to uppercase."""
        snapshot = TelescopeSnapshot(
            telescope_code="test",
            version=1,
            name="Test Telescope",
            recorded_at=datetime.now(tz=timezone.utc),
        )
        assert snapshot.telescope_code == "TEST"

    @staticmethod
    def test_revision_code_normalization():
        """TelescopeRevision normalizes telescope_code to uppercase."""
        revision = TelescopeRevision(
            telescope_code="test",
            name="Test Telescope",
        )
        assert revision.telescope_code == "TEST"


class TestTelescopeRevisionDiff:
    """Tests for the TelescopeRevision.get_diff method."""

    @staticmethod
    def test_no_diff():
        """get_diff returns None when there are no changes."""
        snapshot = TelescopeSnapshot(
            telescope_code="TEST",
            version=1,
            name="Test Telescope",
            recorded_at=datetime.now(tz=timezone.utc),
            aperture_m=2.0,
        )
        revision = TelescopeRevision(
            telescope_code="TEST",
            name="Test Telescope",
            aperture_m=2.0,
        )
        assert revision.get_diff(snapshot) is None

    @staticmethod
    def test_with_diff():
        """get_diff returns correct diffs when there are changes."""
        snapshot = TelescopeSnapshot(
            telescope_code="TEST",
            version=1,
            name="Test Telescope",
            recorded_at=datetime.now(tz=timezone.utc),
            aperture_m=2.0,
        )
        revision = TelescopeRevision(
            telescope_code="TEST",
            name="Updated Telescope",
            aperture_m=2.5,
        )
        diffs = revision.get_diff(snapshot)
        assert diffs == {
            "name": ("Test Telescope", "Updated Telescope"),
            "aperture_m": (2.0, 2.5),
        }

    @staticmethod
    def test_code_mismatch():
        """get_diff raises InvalidRevisionError for telescope_code mismatch."""
        snapshot = TelescopeSnapshot(
            telescope_code="TEST1",
            version=1,
            name="Test Telescope 1",
            recorded_at=datetime.now(tz=timezone.utc),
        )
        revision = TelescopeRevision(
            telescope_code="TEST2",
            name="Test Telescope 2",
        )
        with pytest.raises(
            catalog_errors.InvalidRevisionError,
            match="telescope_code mismatch with head",
        ):
            revision.get_diff(snapshot)


class TestApplyTelescopePatch:
    """Tests for TelescopePatch.apply_to method."""

    @staticmethod
    def test_apply_patch():
        """Applying a patch updates only specified fields."""
        head = TelescopeSnapshot(
            telescope_code="TEST",
            version=1,
            name="Test Telescope",
            recorded_at=datetime.now(tz=timezone.utc),
            aperture_m=2.0,
        )
        patch = TelescopePatch(
            name="Patched Telescope",
            aperture_m=2.5,
        )
        revised = patch.apply_to(head)
        assert revised.telescope_code == "TEST"
        assert revised.name == "Patched Telescope"
        assert revised.aperture_m == 2.5
