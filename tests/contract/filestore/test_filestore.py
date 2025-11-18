"""Contract tests for filestore implementations.

These tests ensure that any filestore implementation adheres to the expected
behavior defined by the filestore interface. These tests do not depend on
specific implementations, backend, filesystem, or storage technology,but
rather validate the contract that all implementations must fulfill.
"""

import hashlib
import io
from collections.abc import Iterable

import pytest

from calista.adapters.filestore.local import LocalFileStore
from calista.interfaces.filestore import BlobStats, FileStore

# ============================================================================
#                               Fixtures
# ============================================================================

# pylint: disable=redefined-outer-name

NONEXISTENT = "0" * 64  # "SHA-256" that should not exist in any filestore


@pytest.fixture(params=["local"])
def filestore(request: pytest.FixtureRequest, tmp_path) -> Iterable[FileStore]:
    """Return a fresh filestore instance for the requested backend.

    Current params:
      - `"local"` → `LocalFileStore` (local filesystem)

    Extend by adding new identifiers to `params` and branching below to
    construct the corresponding backend. Each invocation yields a brand-new
    store instance for isolation.
    """
    # Select filstore based on param
    match request.param:
        case "local":
            root = tmp_path / "filestore"
            yield LocalFileStore(root=root)
        case _:
            raise ValueError(f"unknown filestore type: {request.param}")


def test_store_and_open_read_roundtrip(filestore: FileStore):
    """Test that storing and then reading bytes returns the original data."""
    data = b"hello"
    stats = filestore.store(io.BytesIO(data))

    assert isinstance(stats, BlobStats)

    with filestore.open_read(stats.sha256) as f:
        assert f.read() == data


def test_store_reads_from_current_position(filestore: FileStore):
    """Test that storing from a stream reads from the current position."""
    buffer = io.BytesIO(b"0123456789")
    buffer.seek(3)

    stats = filestore.store(buffer)

    expected = b"3456789"
    assert stats.size_bytes == len(expected)
    assert stats.sha256 == hashlib.sha256(expected).hexdigest()

    with filestore.open_read(stats.sha256) as f:
        assert f.read() == expected


def test_exists_reports_correct_existence(filestore: FileStore):
    """Test that exists() reports correct existence of blobs."""
    data = b"existence test"
    stats = filestore.store(io.BytesIO(data))

    assert filestore.exists(stats.sha256) is True
    assert filestore.exists(NONEXISTENT) is False


def test_open_read_raises_for_nonexistent_file(filestore: FileStore):
    """Test that open_read raises FileNotFoundError for nonexistent blobs."""
    with pytest.raises(FileNotFoundError) as exc_info:
        filestore.open_read(NONEXISTENT)

    assert exc_info.value.args[0] == f"Blob {NONEXISTENT!r} not found"


@pytest.mark.parametrize(
    "invalid_sha, error_msg",
    [
        ("/invalid", "Invalid CAS key"),
        ("\\invalid", "Invalid CAS key"),
        ("short", "Invalid CAS key length (expected 64 characters)"),
        ("0" * 65, "Invalid CAS key length (expected 64 characters)"),
        ("0" * 62 + ":a", "SHA-256 key contains non-hex characters"),
    ],
    ids=["slashes", "double-slashes", "too-short", "too-long", "non-hex"],
)
def test_open_read_raises_for_invalid_sha256(
    filestore: FileStore, invalid_sha, error_msg
):
    """Test that open_read raises ValueError for invalid SHA-256 keys."""
    with pytest.raises(ValueError) as exc_info:
        filestore.open_read(invalid_sha)

    assert exc_info.value.args[0] == error_msg


@pytest.mark.parametrize(
    "invalid_sha, error_msg",
    [
        ("/invalid", "Invalid CAS key"),
        ("\\invalid", "Invalid CAS key"),
        ("short", "Invalid CAS key length (expected 64 characters)"),
        ("0" * 65, "Invalid CAS key length (expected 64 characters)"),
        ("0" * 62 + ":a", "SHA-256 key contains non-hex characters"),
    ],
    ids=["slashes", "double-slashes", "too-short", "too-long", "non-hex"],
)
def test_exists_raises_for_invalid_sha256(filestore: FileStore, invalid_sha, error_msg):
    """Test that exists raises ValueError for invalid SHA-256 keys."""
    with pytest.raises(ValueError) as exc_info:
        filestore.exists(invalid_sha)
    assert exc_info.value.args[0] == error_msg


def test_store_deduplicates_identical_files(filestore: FileStore):
    """Test that storing identical files results in the same BlobStats."""
    data = b"duplicate me"

    stats1 = filestore.store(io.BytesIO(data))
    stats2 = filestore.store(io.BytesIO(data))

    assert stats1.sha256 == stats2.sha256
    assert stats1.size_bytes == stats2.size_bytes
