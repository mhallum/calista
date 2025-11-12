"""Contract tests for the ExposureIndex interface.

These tests ensure that any implementation of the ExposureIndex interface
adheres to the expected behavior defined by the interface.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

import pytest

from calista.adapters.exposure_index import InMemoryExposureIndex
from calista.interfaces.exposure_index import (
    ExposureIDAlreadyBound,
    SHA256AlreadyBound,
    SHA256NotFoundError,
)

if TYPE_CHECKING:
    from calista.interfaces.exposure_index import ExposureIndex


# Deal with pytest fixtures
# pylint: disable=redefined-outer-name

# --- Fixtures ---


@pytest.fixture(params=["memory"])
def exposure_index(
    request: pytest.FixtureRequest,
) -> Iterable[ExposureIndex]:
    """Return a fresh ExposureIndex instance for the requested backend.

    Supported params:
      - `"memory"` → in-memory ExposureIndex

    Extend by adding new identifiers to `params` and branching below to
    construct the corresponding backend. Each invocation yields a brand-new
    ExposureIndex instance for isolation.
    """

    match request.param:
        case "memory":
            yield InMemoryExposureIndex()
        case _:
            raise ValueError(f"unknown exposure index type: {request.param}")


# --- Tests ---


class TestExposureIndexLookup:
    """Tests for the ExposureIndex.lookup method."""

    @staticmethod
    def test_lookup_nonexistent_sha256_returns_none(
        exposure_index: ExposureIndex,
    ) -> None:
        """Test that looking up a nonexistent SHA256 returns None."""
        result = exposure_index.lookup("nonexistent-sha256")
        assert result is None

    @staticmethod
    def test_lookup_existing_sha256_returns_exposure_id(
        exposure_index: ExposureIndex,
    ) -> None:
        """Test that looking up an existing SHA256 returns the correct exposure ID."""
        sha256 = "existing-sha256"
        exposure_id = "exposure-123"

        exposure_index.register(sha256, exposure_id)

        result = exposure_index.lookup(sha256)
        assert result == exposure_id


class TestExposureIndexRegister:
    """Tests for the ExposureIndex.register method."""

    @staticmethod
    def test_register_new_pair_succeeds(exposure_index: ExposureIndex) -> None:
        """Test that registering a new (sha256, exposure_id) pair succeeds."""
        sha256 = "new-sha256"
        exposure_id = "exposure-456"

        exposure_index.register(sha256, exposure_id)

        result = exposure_index.lookup(sha256)
        assert result == exposure_id

    @staticmethod
    def test_register_existing_pair_is_idempotent(
        exposure_index: ExposureIndex,
    ) -> None:
        """Test that registering an existing (sha256, exposure_id) pair is idempotent."""
        sha256 = "existing-sha256"
        exposure_id = "exposure-789"

        exposure_index.register(sha256, exposure_id)
        # Registering the same pair again should not raise an error
        exposure_index.register(sha256, exposure_id)

        result = exposure_index.lookup(sha256)
        assert result == exposure_id

    @staticmethod
    def test_register_sha256_already_bound_raises(
        exposure_index: ExposureIndex,
    ) -> None:
        """Test that registering a SHA256 already bound to a different exposure ID raises an error."""
        sha256 = "bound-sha256"
        exposure_id_1 = "exposure-101"
        exposure_id_2 = "exposure-202"

        exposure_index.register(sha256, exposure_id_1)

        with pytest.raises(
            SHA256AlreadyBound,
        ) as exc_info:
            exposure_index.register(sha256, exposure_id_2)

        error = exc_info.value
        assert error.sha256 == sha256
        assert error.exposure_id == exposure_id_1

    @staticmethod
    def test_register_exposure_id_already_bound_raises(
        exposure_index: ExposureIndex,
    ) -> None:
        """Test that registering an exposure ID already bound to a different SHA256 raises an error."""
        sha256_1 = "bound-sha256-1"
        sha256_2 = "bound-sha256-2"
        exposure_id = "exposure-303"

        exposure_index.register(sha256_1, exposure_id)

        with pytest.raises(
            ExposureIDAlreadyBound,
        ) as exc_info:
            exposure_index.register(sha256_2, exposure_id)

        error = exc_info.value
        assert error.exposure_id == exposure_id
        assert error.sha256 == sha256_1


class TestExposureIndexDeprecate:
    """Tests for the ExposureIndex.deprecate method."""

    @staticmethod
    def test_deprecate_existing_sha256_removes_the_index(
        exposure_index: ExposureIndex,
    ) -> None:
        """Test that deprecating an existing SHA256 removes the index entry."""
        sha256 = "deprecate-sha256"
        exposure_id = "exposure-404"

        exposure_index.register(sha256, exposure_id)

        exposure_index.deprecate(sha256)

        result = exposure_index.lookup(sha256)
        assert result is None

    @staticmethod
    def test_deprecate_nonexistent_sha256_raises(
        exposure_index: ExposureIndex,
    ) -> None:
        """Test that deprecating a nonexistent SHA256 raises an error."""
        sha256 = "nonexistent-sha256"

        with pytest.raises(
            SHA256NotFoundError,
        ) as exc_info:
            exposure_index.deprecate(sha256)

        error = exc_info.value
        assert error.sha256 == sha256
