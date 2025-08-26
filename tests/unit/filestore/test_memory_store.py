"""Unit tests for the in-memory filestore backend (`MemoryFileStore`).

These tests validate backend-specific behavior and internals that the
backend-agnostic contract suite does not cover, including:

- Single-copy deduplication in the internal object map.
- Writer lifecycle details (idempotent `commit()`, `abort()` semantics,
  `committed` property transitions, and empty-write handling).
- Stream independence for multiple `open_read()` handles.
- URI/size reporting in `stat()`.
- Concurrency dedup with many simultaneous ingests.
"""

from __future__ import annotations

import hashlib
import io
from concurrent.futures import ThreadPoolExecutor

import pytest

from calista.adapters.filestore.interface import IntegrityError, NotFound
from calista.adapters.filestore.memory import MemoryFileStore

## Adjust pylint to deal with fixtures
# pylint: disable=redefined-outer-name

# ============================================================================
#                              Fixtures
# ============================================================================


@pytest.fixture
def store() -> MemoryFileStore:
    """Return a fresh in-memory store instance per test (no cross-test state)."""
    return MemoryFileStore()


# ============================================================================
#                              Helpers
# ============================================================================


def sha256_digest(data: bytes) -> str:
    """Compute the canonical ``sha256:<hex>`` digest for ``data``."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


# ============================================================================
#                              Tests
# ============================================================================


def test_put_bytes_installs_once_and_matches_data(store: MemoryFileStore):
    """`put_bytes` stores the payload once and returns the expected digest."""
    data = b"hello"
    info = store.put_bytes(data)
    assert info.digest == sha256_digest(data)

    # internal map contains exactly one object keyed by digest
    # pylint: disable=protected-access
    assert set(store._objects.keys()) == {info.digest}  # type: ignore # noqa: SLF001
    assert store._objects[info.digest] == data  # type: ignore # noqa: SLF001


def test_duplicate_put_bytes_does_not_duplicate_storage(store: MemoryFileStore):
    """Ingesting the same bytes twice yields one digest and one stored copy."""
    data = b"same-bytes"
    d1 = store.put_bytes(data).digest
    d2 = store.put_bytes(data).digest
    assert d1 == d2
    # only one physical object stored
    # pylint: disable=protected-access
    assert len(store._objects) == 1  # type: ignore # noqa: SLF001


def test_expected_digest_mismatch_raises_and_does_not_install(store: MemoryFileStore):
    """Integrity guard mismatch raises and does not modify store contents."""
    data = b"payload"
    wrong = sha256_digest(b"other")
    with store.open_write() as w:
        w.write(data)
        with pytest.raises(IntegrityError):
            w.commit(expected_digest=wrong)
    # nothing installed on mismatch
    # pylint: disable=protected-access
    assert len(store._objects) == 0  # type: ignore # noqa: SLF001


def test_commit_idempotent_returns_same_blobstat_object(store: MemoryFileStore):
    """Calling `commit()` twice returns the same BlobStat object (idempotent)."""
    data = b"abc"
    with store.open_write() as w:
        w.write(data)
        stat1 = w.commit()
        stat2 = w.commit()  # idempotent repeat
    assert stat1 is stat2
    assert stat1.digest == sha256_digest(data)


def test_abort_idempotent_and_noop_after_commit(store: MemoryFileStore):
    """`abort()` is idempotent and a no-op after a successful `commit()`."""
    data = b"abc"
    with store.open_write() as w:
        w.write(data)
        stat = w.commit()
        # commit finished; abort should be no-op
        w.abort()
        w.abort()
    # pylint: disable=protected-access
    assert set(store._objects.keys()) == {stat.digest}  # type: ignore # noqa: SLF001


def test_commit_after_abort_or_close_raises_and_does_not_install(
    store: MemoryFileStore,
):
    """`commit()` after `abort()` or `close()` raises and stores nothing."""
    # pylint: disable=protected-access
    # abort then commit -> ValueError, nothing installed
    w = store.open_write()
    w.write(b"zzz")
    w.abort()
    with pytest.raises(ValueError):
        w.commit()
    assert len(store._objects) == 0  # type: ignore # noqa: SLF001
    w.close()

    # close then commit -> ValueError, nothing installed
    w2 = store.open_write()
    w2.write(b"yyy")
    w2.close()
    with pytest.raises(ValueError):
        w2.commit()
    assert len(store._objects) == 0  # type: ignore # noqa: SLF001


def test_open_read_returns_new_stream_each_time(store: MemoryFileStore):
    """Each call to `open_read()` returns an independent stream at position 0.

    Reading from one stream must not advance the other; both should produce the
    full payload when read independently.
    """
    data = b"streaming"
    digest = store.put_bytes(data).digest

    # Open two separate handles and verify independence
    with store.open_read(digest) as f1, store.open_read(digest) as f2:
        assert f1 is not f2  # distinct stream objects

        # f1 read should not affect f2's position
        expected = b"str"
        assert f1.read(3) == expected
        assert f2.read(3) == expected

        # Remaining bytes should match for each handle
        assert f1.read() == data[3:]
        assert f2.read() == data[3:]


def test_stat_reports_size_and_mem_uri(store: MemoryFileStore):
    """`stat()` returns the digest, exact size, and a `mem://<digest>` URI."""
    data = b"x" * 123
    info = store.put_bytes(data)
    stats = store.stat(info.digest)
    assert stats.digest == info.digest
    data_size = 123
    assert stats.size == data_size
    assert stats.uri == f"mem://{info.digest}"


def test_open_read_and_stat_not_found(store: MemoryFileStore):
    """Missing digests raise `NotFound` for both `open_read` and `stat`."""
    missing = "sha256:" + "0" * 64
    with pytest.raises(NotFound):
        store.open_read(missing)
    with pytest.raises(NotFound):
        store.stat(missing)


def test_readall_is_independent_copy(store: MemoryFileStore):
    """`readall()` returns bytes equal to stored data (and does not mutate it)."""
    data = b"copy-me"
    d = store.put_bytes(data).digest
    out = store.readall(d)
    assert out == data
    # mutate the returned bytes (via create new) to ensure store unchanged
    assert store.readall(d) == data  # still original


def test_put_stream_consumes_but_does_not_close(store: MemoryFileStore):
    """`put_stream` reads to EOF but must not close the caller's stream."""
    data = b"streamed"
    bio = io.BytesIO(data)
    start = bio.tell()
    info = store.put_stream(bio, chunk_size=2)
    assert info.digest == sha256_digest(data)
    assert not bio.closed
    assert bio.tell() >= start + len(data)


def test_concurrent_duplicate_ingest_dedup_internals(store: MemoryFileStore):
    """Concurrent identical ingests deduplicate to one stored object."""
    # pylint: disable=protected-access

    data = b"concurrent"

    def worker():
        return store.put_bytes(data).digest

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(worker) for _ in range(16)]
        digests = [f.result() for f in futures]
    # still only one stored object
    assert len(store._objects) == 1  # type: ignore # noqa: SLF001
    assert store._objects[digests[0]] == data  # type: ignore # noqa: SLF001


def test_writer_committed_property_transitions_commit(store: MemoryFileStore):
    """`committed` is False → True only after a successful `commit()`; sticky thereafter."""
    with store.open_write() as file:
        # fresh writer: not committed
        assert file.committed is False

        # after write: still not committed
        file.write(b"abc")
        assert file.committed is False

        # after commit: committed True
        stat1 = file.commit()
        assert file.committed is True

        # idempotent commit: still committed, same BlobStat
        stat2 = file.commit()
        assert stat2 is stat1
        assert file.committed is True

        # abort after commit is a no-op; committed stays True
        file.abort()
        assert file.committed is True


def test_writer_committed_property_after_abort_and_context_exit(store: MemoryFileStore):
    """`committed` remains False after `abort()` and on context exit without commit."""
    # abort path: never committed
    w = store.open_write()
    w.write(b"x")
    w.abort()
    assert w.committed is False
    w.close()

    # context exit without commit → abort in __exit__, committed stays False
    with store.open_write() as w2:
        w2.write(b"y")
        assert w2.committed is False
    # after exiting the context, still not committed
    assert w2.committed is False


def test_writer_write_empty_on_fresh_writer_returns_zero_and_commits_empty_blob(
    store: MemoryFileStore,
):
    """Writing empty bytes returns 0; committing yields the empty-blob digest."""
    empty_bytes = b""
    with store.open_write() as w:
        n = w.write(empty_bytes)  # hit the branch: if not data -> return 0
        assert n == 0
        stat = w.commit()  # commit an empty object
    expected = "sha256:" + hashlib.sha256(empty_bytes).hexdigest()
    assert stat.digest == expected
    # object exists and round-trips
    assert store.exists(expected)
    assert store.readall(expected) == empty_bytes


def test_writer_write_empty_after_data_no_effect(store: MemoryFileStore):
    """Empty writes after data do not affect the digest or stored bytes."""
    payload = b"abc123"
    expected = "sha256:" + hashlib.sha256(payload).hexdigest()

    with store.open_write() as w:
        n1 = w.write(payload)
        n2 = w.write(b"")  # hit the branch again; should be a no-op
        assert n1 == len(payload)
        assert n2 == 0
        stat = w.commit()

    assert stat.digest == expected
    assert store.readall(expected) == payload


def test_writer_multiple_empty_writes_then_commit_is_empty_blob(store: MemoryFileStore):
    """Multiple empty writes followed by commit produce the empty-blob digest."""
    with store.open_write() as file:
        assert file.write(b"") == 0
        assert file.write(b"") == 0
        stat = file.commit()
    expected = "sha256:" + hashlib.sha256(b"").hexdigest()
    assert stat.digest == expected
