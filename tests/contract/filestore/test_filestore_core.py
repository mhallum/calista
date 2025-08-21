"""Contract tests for the CAS filestore API.

This module exercises backend-agnostic behavior of `AbstractFileStore`:
- basic ingest/lookup (`put_bytes`, `open_read`, `readall`, `stat`, `exists`)
- writer lifecycle (context exit, commit/abort rules, idempotency)
- integrity guards (`expected_digest`)
- path ingestion error branches (nonexistent vs directory)

Helpers below keep assertions precise without duplicating production code.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from calista.adapters.filestore.api import (
    AbstractFileStore,
    BlobStat,
    IntegrityError,
    NotFound,
)

HEX_RE = re.compile(r"^[0-9a-fA-F]+$")

# ===========================================================================
#                            Helper functions
# ===========================================================================


def split_digest(digest: str) -> tuple[str, str]:
    """Validate and split a digest string into `(algorithm, hex)`.

    The function enforces the canonical `<algorithm>:<hex>` shape and that the hex
    portion contains only hex digits. It lower-cases both parts to simplify
    equality checks in tests.
    """
    parts = digest.split(":", 1)
    expected_num_parts = 2  # The algorithm and hex parts
    assert len(parts) == expected_num_parts and parts[0] and parts[1], (
        f"bad digest format: {digest!r}"
    )
    algorithm, hex_value = parts[0].lower(), parts[1].lower()
    assert HEX_RE.match(hex_value), f"non-hex digest payload: {digest!r}"
    return algorithm, hex_value


def compute_digest(algorithm: str, data: bytes) -> str | None:
    """Compute `<algorithm>:<hex>` for supported algorithms.

    Currently only `sha256` is exercised in tests; for any other algorithm the
    function returns `None` so callers can skip the equality check gracefully.
    """
    match algorithm.lower():
        case "sha256":
            hash_object = hashlib.sha256()
        case _:
            return None
    hash_object.update(data)
    return f"{algorithm.lower()}:{hash_object.hexdigest()}"


def mutate_digest(digest: str) -> str:
    """Return a *different* digest string with the same algorithm.

    This is useful to fabricate a missing digest or an integrity-guard mismatch:
    it flips the last hex nibble to ensure the result is distinct but well-formed.
    """
    algorithm, hex_digest = split_digest(digest)
    last = hex_digest[-1]
    # flip last hex digit
    alt = "0" if last != "0" else "1"  # pylint: disable=magic-value-comparison
    return f"{algorithm}:{hex_digest[:-1]}{alt}"


def mk_missing(tmp: Path) -> Path:
    """Return a path that does not exist."""
    return tmp / "nope.bin"


def mk_dir(tmp: Path) -> Path:
    """Create and return a directory path (to trigger IsADirectoryError)."""
    d = tmp / "dir"
    d.mkdir()
    return d


# ===========================================================================
#                               Tests
# ===========================================================================


def test_put_bytes_and_stat_roundtrip(store: AbstractFileStore, arbitrary_bytes: bytes):
    """Ingest via `put_bytes`; `stat` matches digest and size (if provided)."""

    info = store.put_bytes(arbitrary_bytes)
    assert isinstance(info, BlobStat)
    algorithm, _ = split_digest(info.digest)

    st = store.stat(info.digest)
    assert st.digest == info.digest
    assert st.size is None or st.size == len(arbitrary_bytes)

    if expected := compute_digest(algorithm, arbitrary_bytes):
        assert info.digest == expected


def test_open_read_and_readall(store: AbstractFileStore, arbitrary_bytes: bytes):
    """`open_read` stream and `readall` both round-trip the same bytes."""
    info = store.put_bytes(arbitrary_bytes)
    with store.open_read(info.digest) as file:
        head = file.read(10)
        assert head == arbitrary_bytes[:10]
        rest = file.read()
    assert head + rest == arbitrary_bytes
    assert store.readall(info.digest) == arbitrary_bytes


def test_exists_true_false(store: AbstractFileStore, arbitrary_bytes: bytes):
    """`exists` is true for present digests and false for mutated digests."""
    info = store.put_bytes(arbitrary_bytes)
    assert store.exists(info.digest)
    assert not store.exists(mutate_digest(info.digest))


def test_not_found_errors(store: AbstractFileStore, arbitrary_bytes: bytes):
    """`stat`/`open_read` raise `NotFound` for missing digests."""
    info = store.put_bytes(arbitrary_bytes)
    missing = mutate_digest(info.digest)
    with pytest.raises(NotFound):
        store.stat(missing)
    with pytest.raises(NotFound):
        store.open_read(missing)


def test_writer_context_abort_on_exit_without_commit(
    store: AbstractFileStore, arbitrary_bytes: bytes
):
    """Leaving writer context without `commit()` must not install an object."""
    with store.open_write() as file:
        file.write(arbitrary_bytes)  # no commit
    info2 = store.put_bytes(arbitrary_bytes)
    assert store.exists(info2.digest)


def test_writer_write_after_commit_or_abort_raises(
    store: AbstractFileStore, arbitrary_bytes: bytes
):
    """`write()` after `commit()` or `abort()` raises `ValueError`."""
    with store.open_write() as file:
        file.write(arbitrary_bytes)
        info = file.commit()
        assert isinstance(info, BlobStat)
        with pytest.raises(ValueError):
            file.write(b"x")
    file2 = store.open_write()
    file2.write(b"abc")
    file2.abort()
    with pytest.raises(ValueError):
        file2.write(b"x")
    file2.close()


def test_commit_idempotent_for_duplicate_bytes(
    store: AbstractFileStore, arbitrary_bytes: bytes
):
    """Ingesting identical bytes twice yields the same digest (dedup)."""
    a = store.put_bytes(arbitrary_bytes)
    b = store.put_bytes(bytes(arbitrary_bytes))
    assert a.digest == b.digest


def test_integrity_guard_ok_and_fail(store: AbstractFileStore, arbitrary_bytes: bytes):
    """`commit(expected_digest=…)` accepts the right digest and rejects a mismatch."""
    info = store.put_bytes(arbitrary_bytes)
    with store.open_write() as file:
        file.write(arbitrary_bytes)
        info2 = file.commit(expected_digest=info.digest)
    assert info2.digest == info.digest
    bad_expected = mutate_digest(info.digest)
    with store.open_write() as file:
        file.write(arbitrary_bytes)
        with pytest.raises(IntegrityError):
            file.commit(expected_digest=bad_expected)


def test_zero_byte_blob_digest_and_roundtrip(store: AbstractFileStore):
    """Empty payload produces the known SHA-256 of empty string and round-trips."""
    empty = b""
    info = store.put_bytes(empty)
    expected = "sha256:" + hashlib.sha256(empty).hexdigest()
    assert info.digest == expected
    assert store.readall(info.digest) == empty
    stats = store.stat(info.digest)
    if stats.size is not None:
        assert stats.size == 0


def test_multiple_writes_then_commit_matches_put_bytes(
    store: AbstractFileStore, arbitrary_bytes: bytes
):
    """Chunked writes followed by `commit()` equals `put_bytes` digest."""
    mid = len(arbitrary_bytes) // 2
    with store.open_write() as file:
        file.write(arbitrary_bytes[:mid])
        file.write(arbitrary_bytes[mid:])
        info = file.commit()
    expected = "sha256:" + hashlib.sha256(arbitrary_bytes).hexdigest()
    assert info.digest == expected


def test_close_then_commit_raises_and_abort_idempotent(store: AbstractFileStore):
    """`commit()` after `close()` raises; `abort()` is idempotent and safe."""
    file = store.open_write()
    file.write(b"abc")
    file.close()
    with pytest.raises(ValueError):
        file.commit()
    file.abort()
    file.abort()


def test_commit_then_abort_is_noop(store: AbstractFileStore, arbitrary_bytes: bytes):
    """`abort()` after a successful `commit()` is a no-op (no deletion)."""
    with store.open_write() as file:
        file.write(arbitrary_bytes)
        info = file.commit()
    assert store.exists(info.digest)


@pytest.mark.parametrize(
    "make_path, exc",
    [
        pytest.param(mk_missing, FileNotFoundError, id="missing-file"),
        pytest.param(mk_dir, IsADirectoryError, id="is-a-directory"),
    ],
)
def test_put_path_error_branches(
    store: AbstractFileStore,
    tmp_path: Path,
    make_path: Callable[[Path], Path],
    exc: type[BaseException],
):
    """`put_path` distinguishes missing files vs directories with clear errors."""
    target = make_path(tmp_path)
    with pytest.raises(exc):
        store.put_path(target)
