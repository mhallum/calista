"""Integration tests for the LocalFileStore adapter.

This module contains integration tests that validate the LocalFileStore's behavior
with the local filesystem. The LocalFileStore should also pass the contract tests defined
in `tests/contract/filestore/test_filestore.py`. These are additional tests specific to
the LocalFileStore implementation.
"""

import hashlib
import io
import tempfile
from pathlib import Path

from calista.adapters.filestore.local import CHUNK_SIZE, LocalFileStore


def _get_root(filestore):
    return filestore._root  # pylint: disable=protected-access


def test_local_filestore_initialization(tmp_path):
    """Test that LocalFileStore initializes correctly with a given root path."""
    root = tmp_path / "filestore_root"
    root.mkdir(parents=True, exist_ok=True)
    store = LocalFileStore(root=root)
    assert _get_root(store).exists()
    assert _get_root(store).is_dir()


def test_local_filestore_creates_root_if_missing(tmp_path):
    """Test that LocalFileStore creates the root directory if it does not exist."""
    top_level_dir = tmp_path / "top_level_dir"
    top_level_dir.mkdir(parents=True, exist_ok=True)
    root_path = top_level_dir / "calista" / "new_filestore_root"
    assert not root_path.exists()

    LocalFileStore(root=root_path)
    assert root_path.exists()
    assert root_path.is_dir()


def test_local_filestore_stores_file_correctly(tmp_path):
    """Test that LocalFileStore stores a file and returns correct BlobStats."""

    root = tmp_path / "filestore"
    root.mkdir(parents=True, exist_ok=True)
    filestore = LocalFileStore(root=root)

    data = b"sample data for testing"
    stats = filestore.store(io.BytesIO(data))

    assert stats.size_bytes == len(data)
    assert stats.sha256 == hashlib.sha256(data).hexdigest()

    # Verify that the file exists in the filestore
    assert filestore.exists(stats.sha256)

    # Verify that the stored file can be read back correctly
    with filestore.open_read(stats.sha256) as f:
        read_data = f.read()
    assert read_data == data

    # Verify the file is stored at the correct path
    expected_path = filestore._determine_cas_path(stats.sha256)  # pylint: disable=protected-access
    assert expected_path.exists()
    assert expected_path.is_file()
    with expected_path.open("rb") as f:
        stored_data = f.read()
    assert stored_data == data


def test_local_filestore_sharding(tmp_path):
    """Test that LocalFileStore correctly shards files into subdirectories."""

    root = tmp_path / "filestore"
    root.mkdir(parents=True, exist_ok=True)
    filestore = LocalFileStore(root=root)
    data = b"another sample data for sharding test"
    stats = filestore.store(io.BytesIO(data))

    # Determine expected shard path
    sha256 = stats.sha256
    shard_dir_a = sha256[:2]
    shard_dir_b = sha256[2:4]
    expected_path = _get_root(filestore) / shard_dir_a / shard_dir_b / sha256

    assert expected_path.exists()
    assert expected_path.is_file()


def test_store_uses_root_for_temp_files(monkeypatch, tmp_path):
    """Test that LocalFileStore uses the correct root directory for temporary files."""

    root = tmp_path / "filestore"

    # Grab original before patching
    orig_named_tempfile = tempfile.NamedTemporaryFile

    store = LocalFileStore(root)

    captured: dict[str, Path | None] = {}

    def fake_named_tempfile(*, dir=None, delete=False):  # pylint: disable=redefined-builtin
        # record what LocalFileStore passed
        captured["dir"] = dir
        # delegate to the real function (only with the args we care about)
        return orig_named_tempfile(dir=root, delete=delete)

    monkeypatch.setattr(
        "calista.adapters.filestore.local.tempfile.NamedTemporaryFile",
        fake_named_tempfile,
    )

    store.store(io.BytesIO(b"data"))

    assert captured["dir"] == root


def test_temp_file_deleted_on_existing_blob(tmp_path):
    """Test that temporary files are deleted if the blob already exists."""

    root = tmp_path / "filestore"
    root.mkdir(parents=True, exist_ok=True)
    filestore = LocalFileStore(root=root)
    data = b"data that will be stored"
    stats = filestore.store(io.BytesIO(data))

    # Store the same data again
    stats2 = filestore.store(io.BytesIO(data))

    assert stats2.sha256 == stats.sha256
    assert stats2.size_bytes == stats.size_bytes

    # Verify that no temporary files remain in the filestore root
    root_path = _get_root(filestore)
    temp_files = list(root_path.glob("tmp*"))
    assert len(temp_files) == 0


def test_store_reports_total_size_across_chunks(tmp_path):
    """Test that LocalFileStore.store reports the correct total size for large files."""

    root = tmp_path / "filestore"
    store = LocalFileStore(root)

    # Force at least 2 chunks
    data = b"x" * (CHUNK_SIZE * 2 + 10)

    stats = store.store(io.BytesIO(data))

    assert stats.size_bytes == len(data)


def test_store_reads_in_bounded_chunks(tmp_path):
    """Test that LocalFileStore reads input streams in bounded chunks."""

    class LoggingStream(io.BytesIO):
        """BytesIO that logs the size argument of each read call."""

        def __init__(self, data: bytes):
            super().__init__(data)
            self.calls: list[int | None] = []

        def read(self, size: int | None = -1) -> bytes:
            self.calls.append(size)
            if size is None:
                size = -1
            return super().read(size)

    root = tmp_path / "filestore"
    store = LocalFileStore(root)

    data = b"x" * (2 * CHUNK_SIZE + 10)
    stream = LoggingStream(data)

    store.store(stream)

    # All but possibly the last read should use CHUNK_SIZE
    assert all((n == CHUNK_SIZE) for n in stream.calls[:-1])
    # And we must never pass None as the size
    assert None not in stream.calls


def test_store_is_idempotent_for_existing_parent_dir(tmp_path, monkeypatch):
    """Test that LocalFileStore.store is idempotent when parent directories exist."""

    root = tmp_path / "filestore"
    store = LocalFileStore(root)

    # Force all blobs to live under the same parent directory
    def fake_determine_cas_path(self: LocalFileStore, sha256: str) -> Path:
        return self._root / "aa" / "bb" / sha256  # pylint: disable=protected-access

    monkeypatch.setattr(
        LocalFileStore,
        "_determine_cas_path",
        fake_determine_cas_path,
    )

    # First store creates the parent dirs
    store.store(io.BytesIO(b"first blob"))

    # Second store should NOT crash even though parent dir exists
    store.store(io.BytesIO(b"second blob"))
