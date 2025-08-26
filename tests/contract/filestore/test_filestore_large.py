"""Large-blob smoke tests for the CAS filestore.

These tests exercise end-to-end ingest/lookup on multi-MiB payloads with
intentionally awkward chunk sizes to catch off-by-one and buffering bugs.

Includes:
- `put_bytes` + streamed reads in large, uneven chunks.
- `put_path` with Unicode/spacey paths and odd writer chunk sizes.
- `put_stream` ensuring the caller-owned stream remains open.
- Optional size verification via `stat()` (size MAY be None per contract).

Marked `@pytest.mark.slow` so day-to-day CI can skip them if wanted.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from calista.adapters.filestore.interface import AbstractFileStore

# Payload sizes (~5 MiB and ~20 MiB)
SIZES = [5 * 1024 * 1024, 20 * 1024 * 1024]
# Writer chunk sizes that don't align with MiB boundaries (stress chunking)
PUT_CHUNKS = [(1024 * 1024) - 3, (2 * 1024 * 1024) + 7]
# Reader chunk size (odd to stress buffering)
READ_CHUNK = 777_777


def _pattern_bytes(n: int) -> bytes:
    """Return a deterministic 0..255 repeating byte pattern of length `n`.

    This produces stable content independent of randomness so digests are
    reproducible across runs and ingestion methods.
    """
    pat = bytes(range(256))
    return (pat * ((n // 256) + 1))[:n]


@pytest.mark.slow
@pytest.mark.parametrize("size", SIZES)
def test_large_blob_put_bytes_and_stream_read(store: AbstractFileStore, size: int):
    """Ingest a large payload via `put_bytes` and verify streamed reads.

    - Confirms the returned digest equals the SHA-256 of the data.
    - Reads the blob back in large, uneven chunks and verifies the reassembled
      bytes match exactly.
    - Checks `stat().size` if provided by the backend.
    """
    data = _pattern_bytes(size)
    expected = "sha256:" + hashlib.sha256(data).hexdigest()
    info = store.put_bytes(data)
    assert info.digest == expected
    assert store.readall(info.digest) == data
    got = bytearray()
    with store.open_read(info.digest) as file:
        while chunk := file.read(READ_CHUNK):  # pylint: disable=while-used
            if not chunk:
                break
            got.extend(chunk)
    assert bytes(got) == data
    st = store.stat(info.digest)
    if st.size is not None:
        assert st.size == size


@pytest.mark.slow
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("put_chunk", PUT_CHUNKS)
def test_large_blob_put_path_and_put_stream_variants(
    store: AbstractFileStore, tmp_path: Path, size: int, put_chunk: int
):
    """Ingest large payloads via `put_path` and `put_stream` with odd chunk sizes.

    - Uses a real file path containing spaces and Unicode characters.
    - Verifies `put_path(..., chunk_size=put_chunk)` digest and full round-trip.
    - Verifies `put_stream` with the same chunk size and that the caller's
      stream remains open.
    - Confirms `open_read` head+tail concatenation equals the original bytes.
    """
    data = _pattern_bytes(size)
    expected = "sha256:" + hashlib.sha256(data).hexdigest()
    p = tmp_path / "nested dir" / "unicodé_📄.bin"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    info1 = store.put_path(p, chunk_size=put_chunk)
    assert info1.digest == expected
    assert store.readall(info1.digest) == data
    bio = io.BytesIO(data)
    info2 = store.put_stream(bio, chunk_size=put_chunk)
    assert not bio.closed
    assert info2.digest == expected
    with store.open_read(info2.digest) as fp:
        head = fp.read(10)
        tail = fp.read()
    assert head + tail == data
