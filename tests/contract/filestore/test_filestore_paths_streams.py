"""Contract tests for path- and stream-oriented filestore behaviors.

Covers:
- `put_path` with regular files, symlink policy (refuse by default, allow with flag),
  chunking, and Unicode/space-containing paths.
- `put_stream` ensuring the caller-owned stream remains open.
- `open_read` file-like semantics (`read(0)` and optional `seek` support).
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest

from calista.adapters.filestore.api import AbstractFileStore


def test_put_path_and_symlink_policy(
    store: AbstractFileStore, tmp_path: Path, arbitrary_bytes: bytes
):
    """`put_path` accepts regular files, refuses symlinks by default, and allows
    them only with `follow_symlinks=True`."""
    p = tmp_path / "blob.bin"
    p.write_bytes(arbitrary_bytes)
    info = store.put_path(p)
    assert store.exists(info.digest)

    link = tmp_path / "link.bin"
    try:
        link.symlink_to(p)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")
    else:
        with pytest.raises(ValueError):
            store.put_path(link)
        info2 = store.put_path(link, follow_symlinks=True)
        assert info2.digest == info.digest


def test_put_path_chunking_and_str_path(
    store: AbstractFileStore, tmp_path: Path, arbitrary_bytes: bytes
):
    """`put_path` honors custom chunk sizes and accepts both `Path` and `str`."""
    p = tmp_path / "chunk.bin"
    p.write_bytes(arbitrary_bytes)
    info = store.put_path(p, chunk_size=7)
    assert store.readall(info.digest) == arbitrary_bytes
    info2 = store.put_path(str(p))
    assert info2.digest == info.digest


def test_put_path_unicode_and_expected_digest(
    store: AbstractFileStore, tmp_path: Path, arbitrary_bytes: bytes
):
    """`put_path` handles Unicode/spacey paths and respects `expected_digest`."""
    p = tmp_path / "dir with spaces" / "unicodé_📄.bin"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(arbitrary_bytes)
    info = store.put_path(p)
    assert store.readall(info.digest) == arbitrary_bytes
    expected = "sha256:" + hashlib.sha256(arbitrary_bytes).hexdigest()
    guarded = store.put_path(p, expected_digest=expected)
    assert guarded.digest == expected


def test_put_stream_keeps_stream_open(store: AbstractFileStore, arbitrary_bytes: bytes):
    """`put_stream` must consume the stream to EOF but not close it."""
    bio = io.BytesIO(arbitrary_bytes)
    info = store.put_stream(bio, chunk_size=7)
    assert not bio.closed
    assert store.exists(info.digest)


def test_open_read_is_streamlike_and_seek(
    store: AbstractFileStore, arbitrary_bytes: bytes
):
    """`open_read` returns a file-like stream where `read(0)` is a no-op; if
    seekable, `seek` + `read` returns the expected slice.
    """
    info = store.put_bytes(arbitrary_bytes)
    with store.open_read(info.digest) as file:
        expected_empty_first_index = b""  # empty bytes
        assert file.read(0) == expected_empty_first_index
        if hasattr(file, "seek"):
            file.seek(3)
            assert file.read(4) == arbitrary_bytes[3:7]
