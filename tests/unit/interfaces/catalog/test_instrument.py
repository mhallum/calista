"""Unit tests for instrument catalog data models."""

from datetime import datetime, timezone

import pytest

from calista.interfaces.catalog import errors as catalog_errors
from calista.interfaces.catalog.instrument_catalog import (
    InstrumentPatch,
    InstrumentRevision,
    InstrumentSnapshot,
)

# pylint: disable=magic-value-comparison,too-few-public-methods


class TestInstrumentSnapshotValidation:
    """Tests for instrument snapshot validation."""

    @staticmethod
    def test_non_utc_recorded_at():
        """Test non-UTC recorded_at raises InvalidSnapshotError."""
        non_utc_dt = datetime.now()  # naive datetime, not UTC
        with pytest.raises(
            catalog_errors.InvalidSnapshotError,
            match="recorded_at must be timezone-aware UTC",
        ):
            InstrumentSnapshot(
                instrument_code="A",
                version=1,
                name="Test Instrument A",
                recorded_at=non_utc_dt,
            )

    @staticmethod
    def test_valid_snapshot():
        """Test a valid instrument snapshot passes validation."""
        snapshot = InstrumentSnapshot(
            instrument_code="TEST",
            version=1,
            name="Test Instrument",
            recorded_at=datetime.now(tz=timezone.utc),
            mode="imaging",
        )
        assert snapshot.instrument_code == "TEST"
        assert snapshot.mode == "imaging"


class TestInstrumentRevisionValidation:
    """Tests for instrument revision validation errors."""

    @staticmethod
    def test_valid_revision():
        """Test a valid instrument revision passes validation."""
        revision = InstrumentRevision(
            instrument_code="TEST",
            name="Test Instrument",
            mode="spectroscopy",
        )
        assert revision.instrument_code == "TEST"
        assert revision.mode == "spectroscopy"


class TestInstrumentCodeNormalization:
    """Tests for instrument code normalization to uppercase."""

    @staticmethod
    def test_snapshot_code_normalization():
        """InstrumentSnapshot normalizes instrument_code to uppercase."""
        snapshot = InstrumentSnapshot(
            instrument_code="test",
            version=1,
            name="Test Instrument",
            recorded_at=datetime.now(tz=timezone.utc),
        )
        assert snapshot.instrument_code == "TEST"

    @staticmethod
    def test_revision_code_normalization():
        """InstrumentRevision normalizes instrument_code to uppercase."""
        revision = InstrumentRevision(
            instrument_code="test",
            name="Test Instrument",
        )
        assert revision.instrument_code == "TEST"


class TestInstrumentRevisionDiff:
    """Tests for the InstrumentRevision.get_diff method."""

    @staticmethod
    def test_no_diff():
        """get_diff returns None when there are no changes."""
        snapshot = InstrumentSnapshot(
            instrument_code="TEST",
            version=1,
            name="Test Instrument",
            recorded_at=datetime.now(tz=timezone.utc),
            mode="imaging",
        )
        revision = InstrumentRevision(
            instrument_code="TEST",
            name="Test Instrument",
            mode="imaging",
        )
        assert revision.get_diff(snapshot) is None

    @staticmethod
    def test_with_diff():
        """get_diff returns correct diffs when there are changes."""
        snapshot = InstrumentSnapshot(
            instrument_code="TEST",
            version=1,
            name="Test Instrument",
            recorded_at=datetime.now(tz=timezone.utc),
            mode="imaging",
        )
        revision = InstrumentRevision(
            instrument_code="TEST",
            name="Updated Instrument",
            mode="spectroscopy",
        )
        diffs = revision.get_diff(snapshot)
        assert diffs == {
            "name": ("Test Instrument", "Updated Instrument"),
            "mode": ("imaging", "spectroscopy"),
        }

    @staticmethod
    def test_code_mismatch():
        """get_diff raises InvalidRevisionError for instrument_code mismatch."""
        snapshot = InstrumentSnapshot(
            instrument_code="TEST1",
            version=1,
            name="Test Instrument 1",
            recorded_at=datetime.now(tz=timezone.utc),
        )
        revision = InstrumentRevision(
            instrument_code="TEST2",
            name="Test Instrument 2",
        )
        with pytest.raises(
            catalog_errors.InvalidRevisionError,
            match="instrument_code mismatch with head",
        ):
            revision.get_diff(snapshot)


class TestApplyInstrumentPatch:
    """Tests for InstrumentPatch.apply_to method."""

    @staticmethod
    def test_apply_patch():
        """Applying a patch updates only specified fields."""
        head = InstrumentSnapshot(
            instrument_code="TEST",
            version=1,
            name="Test Instrument",
            recorded_at=datetime.now(tz=timezone.utc),
            mode="imaging",
        )
        patch = InstrumentPatch(
            name="Patched Instrument",
            mode="spectroscopy",
        )
        revised = patch.apply_to(head)
        assert revised.instrument_code == "TEST"
        assert revised.name == "Patched Instrument"
        assert revised.mode == "spectroscopy"
