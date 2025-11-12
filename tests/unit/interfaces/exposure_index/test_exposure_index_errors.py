"""Test cases for the ExposureIndex errors."""

from calista.interfaces.exposure_index.errors import (
    ExposureIDAlreadyBound,
    ExposureIDNotFoundError,
    SHA256AlreadyBound,
)


class TestExposureIDAlreadyBound:
    """Tests for the ExposureIDAlreadyBound error."""

    @staticmethod
    def test_attributes() -> None:
        """Test that the attributes are set correctly."""
        exposure_id = "exposure-123"
        sha256 = "sha256-hash-abc"

        error = ExposureIDAlreadyBound(exposure_id, sha256)

        assert error.exposure_id == exposure_id
        assert error.sha256 == sha256

    @staticmethod
    def test_message() -> None:
        """Test that the error message is formatted correctly."""
        exposure_id = "exposure-456"
        sha256 = "sha256-hash-def"

        error = ExposureIDAlreadyBound(exposure_id, sha256)

        expected_message = (
            f"Exposure ID '{exposure_id}' is already bound to SHA256 '{sha256}'."
        )
        assert str(error) == expected_message


class TestSHA256AlreadyBound:
    """Tests for the SHA256AlreadyBound error."""

    @staticmethod
    def test_attributes() -> None:
        """Test that the attributes are set correctly."""
        sha256 = "sha256-hash-xyz"
        exposure_id = "exposure-789"

        error = SHA256AlreadyBound(sha256, exposure_id)

        assert error.sha256 == sha256
        assert error.exposure_id == exposure_id

    @staticmethod
    def test_message() -> None:
        """Test that the error message is formatted correctly."""
        sha256 = "sha256-hash-uvw"
        exposure_id = "exposure-012"

        error = SHA256AlreadyBound(sha256, exposure_id)

        expected_message = (
            f"SHA256 '{sha256}' is already bound to exposure ID '{exposure_id}'."
        )
        assert str(error) == expected_message


class TestExposureIDNotFoundError:
    """Tests for the ExposureIDNotFoundError error."""

    @staticmethod
    def test_attributes() -> None:
        """Test that the attributes are set correctly."""
        exposure_id = "exposure-123"

        error = ExposureIDNotFoundError(exposure_id)

        assert error.exposure_id == exposure_id

    @staticmethod
    def test_message() -> None:
        """Test that the error message is formatted correctly."""
        exposure_id = "exposure-456"

        error = ExposureIDNotFoundError(exposure_id)

        expected_message = f"Exposure ID '{exposure_id}' not found in ExposureIndex."
        assert str(error) == expected_message
