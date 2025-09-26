"""Hypothesis property tests for the CAS filestore API.

These properties exercise backend-agnostic invariants of a content-addressed
store (CAS):

- **Digest stability**: All ingest paths (`put_bytes`, `put_stream`, writer with
  arbitrary chunking) must yield the *same* digest for the same bytes.
- **Chunk partition invariance**: Concatenating arbitrary write chunks equals
  writing the whole payload at once.
- **Integrity guard**: `commit(expected_digest=...)` accepts a matching digest
  and rejects any mismatch.
- **Existence/metadata coherence**: After ingest, `exists()` is true and
  `stat()` (if it provides `size`) matches the payload length.

A `store_factory` fixture returns a **fresh** store per generated example to
avoid state bleed.
"""

from __future__ import annotations

import hashlib
import io
from collections.abc import Callable

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from calista.adapters.filestore.memory import MemoryFileStore
from calista.interfaces.filestore import FileStore, IntegrityError

pytestmark = [pytest.mark.property]

## Adjust pylint to deal with fixtures
# pylint: disable=redefined-outer-name

# ============================================================================
#                               Helpers
# ============================================================================


def sha256_digest(data: bytes) -> str:
    """Return the canonical SHA-256 digest string for ``data``.

    Format: ``"sha256:<hex>"`` (lowercase).
    """
    return "sha256:" + hashlib.sha256(data).hexdigest()


def chunk_by_sizes(b: bytes, sizes: list[int]) -> list[bytes]:
    """Split ``b`` into chunks according to ``sizes``.

    Iterates through ``sizes``, taking each ``n`` bytes from ``b`` in order and
    appending that slice to the result. Negative/zero sizes yield an empty chunk
    without advancing the cursor. If ``sizes`` under-consumes the input, the
    remaining tail is appended as a final chunk. Extra sizes past the end of the
    input are ignored.

    Invariant: ``b == b"".join(chunk_by_sizes(b, sizes))``.
    """
    out: list[bytes] = []
    i = 0
    for n in sizes:
        if i >= len(b):
            break
        chunk_len = n if n > 0 else 0
        out.append(b[i : i + chunk_len])
        i += chunk_len
    if i < len(b):
        out.append(b[i:])
    return out


# ============================================================================
#                               Fixtures
# ============================================================================


# store factory (fresh instance per example)
@pytest.fixture(scope="module")
def store_factory():
    """Factory that returns a **fresh** filestore instance per Hypothesis example."""

    def make() -> FileStore:
        # Add other backends when added
        return MemoryFileStore()

    return make


# ============================================================================
#                               Tests
# ============================================================================


# Keep small for CI (~50), can be larger locally.
_PROPSET = settings(max_examples=50, deadline=None)


# 1) Digest stability across ingest methods: put_bytes, put_stream, writer (random chunk)
@_PROPSET
@given(
    data=st.binary(min_size=0, max_size=64_000),
    chunk=st.integers(min_value=1, max_value=16_384),
)
def test_digest_stability_across_methods(
    store_factory: Callable[[], FileStore], data: bytes, chunk: int
):
    """Same bytes → same digest across all ingest methods and chunkings."""
    store = store_factory()
    expected = sha256_digest(data)

    info1 = store.put_bytes(data)
    assert info1.digest == expected

    bio = io.BytesIO(data)
    info2 = store.put_stream(bio, chunk_size=chunk)
    assert not bio.closed
    assert info2.digest == expected

    with store.open_write() as w:
        for i in range(0, len(data), chunk):
            w.write(data[i : i + chunk])
        info3 = w.commit()
    assert info3.digest == expected


# 2) Chunk partition invariance: writing arbitrary chunk partitions equals writing concatenation
@_PROPSET
@given(
    data=st.binary(min_size=0, max_size=64_000),
    sizes=st.lists(st.integers(min_value=0, max_value=8_192), min_size=0, max_size=20),
)
def test_writer_chunk_partition_invariance(
    store_factory: Callable[[], FileStore], data: bytes, sizes: list[int]
):
    """Writing any partition of chunks yields the same digest as writing once."""
    store = store_factory()
    pieces = chunk_by_sizes(data, sizes)

    with store.open_write() as file:
        for p in pieces:
            file.write(p)
        info_parts = file.commit()

    info_whole = store.put_bytes(data)
    assert info_parts.digest == info_whole.digest


# 3) Integrity guard property: matching digest OK; any mismatch raises
@_PROPSET
@given(data=st.binary(min_size=0, max_size=64_000))
def test_expected_digest_guard_property(
    store_factory: Callable[[], FileStore], data: bytes
):
    """Integrity guard accepts exact match and rejects a one-nibble mismatch."""
    store = store_factory()
    ok = sha256_digest(data)

    with store.open_write() as file:
        # exercise multi-write path too
        if data:
            mid = len(data) // 2
            file.write(data[:mid])
            file.write(data[mid:])
        stat_ok = file.commit(expected_digest=ok)
    assert stat_ok.digest == ok

    # mismatch (flip last nibble)
    bad = ok[:-1] + ("0" if ok[-1] != "0" else "1")  # pylint: disable=magic-value-comparison

    store2 = store_factory()
    with store2.open_write() as file:
        if data:
            file.write(data)
        with pytest.raises(IntegrityError):
            file.commit(expected_digest=bad)


# 4) Exists/stat consistency: after ingest, exists() true; stat digest matches; size (if present) matches
@_PROPSET
@given(data=st.binary(min_size=0, max_size=64_000))
def test_exists_and_stat_consistency(
    store_factory: Callable[[], FileStore], data: bytes
):
    """After ingest, `exists()` is true and `stat()` metadata matches digest/size."""
    store = store_factory()
    info = store.put_bytes(data)
    assert store.exists(info.digest)

    st_ = store.stat(info.digest)
    assert st_.digest == info.digest
    if st_.size is not None:
        assert st_.size == len(data)
