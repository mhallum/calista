"""In-memory Content-Addressed Store (CAS) backend.

This module provides a tiny, dependency-free CAS implementation meant for
**tests**, examples, and local development. Objects are kept entirely in RAM
and addressed by their **content digest** (default: `"sha256:<hex>"`). There is
no persistence across process restarts.

Exports
-------
- MemoryFileStore: Concrete `AbstractFileStore` backed by an in-memory dict.

Key behaviors
-------------
- **Digest identity only**: no path/alias semantics; callers interact via
  `put_*`, `open_read`, and `stat`.
- **Writer semantics**:
  - Bytes are staged in a buffer and hashed incrementally.
  - `commit()` is **idempotent**. If another writer already committed the same
    digest, the staged bytes are discarded and the existing object is used.
  - `expected_digest` is enforced; mismatches raise `IntegrityError`.
  - Leaving a writer context without `commit()` discards staged data (`abort()`).
- **Deduplication**: Only a single copy of bytes exists per digest.
- **Thread-safety**: All installs/lookups happen under an `RLock`, making
  `commit()` atomic with respect to concurrent writers/readers.
- **Durability**: `fsync` hints are ignored (there’s nothing to fsync).

Hash algorithms
---------------
`MemoryFileStore(hash_algorithm="sha256")` selects the algorithm passed to
`hashlib.new()`. If the algorithm is unavailable, construction will fail.
For CALISTA’s default policy, use `"sha256"`.

Typical usage
-------------
    store = MemoryFileStore()
    info = store.put_bytes(b"hello")
    with store.open_read(info.digest) as fp:
        data = fp.read()  # b"hello"
    meta = store.stat(info.digest)  # BlobStat(digest=..., size=5, uri="mem://...")

Notes
-----
- `open_read()` returns a `BytesIO` that the **caller** must close (or use as a
  context manager).
- `stat()` does not read bodies; size is returned from the in-memory map.
- `uri` in `BlobStat` is a locator hint of the form `"mem://<digest>"` and is
  **not** the identity.

Intended scope
--------------
This backend is great for unit/contract tests and ephemeral usage. For
production, use a durable backend (e.g., filesystem or object store) that
honors `fsync`/atomic placement and persists across restarts.
"""

from __future__ import annotations

import hashlib
import io
import threading

from .api import (
    AbstractFileStore,
    AbstractWriter,
    BlobStat,
    IntegrityError,
    NotFound,
)

__all__ = ["MemoryFileStore"]


class MemoryFileStore(AbstractFileStore):
    """In-memory Content-Addressed Store (CAS) backend.

    Stores immutable blobs **entirely in RAM** and addresses them by their
    content digest (`"<algo>:<hex>"`, lowercase). This backend is intended for
    tests, examples, and local development; it is **non-durable** (data is lost
    when the process exits).

    Thread-safety & atomicity
    -------------------------
    All installs/lookups are protected by a reentrant lock, so concurrent
    writers/readers are safe. `commit()` is atomic with respect to other
    `commit()`/`open_read()` calls, and **deduplicates**: if an object with the
    computed digest already exists, the staged bytes are discarded and the
    existing object is used (idempotent commit).

    Hash algorithm
    --------------
    The digest algorithm is chosen at construction and passed to `hashlib.new()`.
    For CALISTA the default is `"sha256"`.

    - `hash_algorithm`: e.g. `"sha256"`, must be supported by `hashlib.new()`.

    Semantics
    ---------
    - `open_write(fsync=True) → AbstractWriter`: returns a staging writer;
      `fsync` is ignored in memory. The writer hashes bytes incrementally and
      commits atomically.
    - `open_read(digest) → io.BytesIO`: returns a stream positioned at 0; the
      **caller** must close it. Raises `NotFound` if the digest is absent.
    - `stat(digest) → BlobStat`: returns cheap metadata without reading bodies,
      including `size` and a hint URI of the form `"mem://<digest>"`. Raises
      `NotFound` if absent.
    - Inherited conveniences: `exists`, `put_bytes`, `put_stream`, `put_path`,
      `readall`.

    Errors
    ------
    - `IntegrityError`: `commit(expected_digest=...)` mismatches the computed digest.
    - `NotFound`: `open_read`/`stat` called for a missing digest.

    Example
    -------
        store = MemoryFileStore()
        info = store.put_bytes(b"hello")
        with store.open_read(info.digest) as fp:
            assert fp.read() == b"hello"
        meta = store.stat(info.digest)  # BlobStat(digest=..., size=5, uri="mem://...")
    """

    def __init__(self, hash_algorithm: str = "sha256") -> None:
        self._hash_algorithm = hash_algorithm.lower()
        self._objects: dict[str, bytes] = {}
        self._lock = threading.RLock()

    # ---- AbstractFileStore ----

    def open_write(self, *, fsync: bool = True) -> AbstractWriter:
        # fsync flag is ignored (no durability in memory)
        return _MemWriter(self, hash_algorithm=self._hash_algorithm)

    def open_read(self, digest: str) -> io.BytesIO:
        with self._lock:
            try:
                data = self._objects[digest]
            except KeyError as e:
                raise NotFound(digest) from e
        # Caller must close the stream; BytesIO supports context manager usage
        return io.BytesIO(data)

    def stat(self, digest: str) -> BlobStat:
        with self._lock:
            try:
                size = len(self._objects[digest])
            except KeyError as exc:
                raise NotFound(digest) from exc
        return BlobStat(digest=digest, size=size, uri=f"mem://{digest}")

    # (inherits: exists, put_path, put_bytes, put_stream, readall)


class _MemWriter(AbstractWriter):  # pylint: disable=too-many-instance-attributes
    """Writer for MemoryFileStore; stages bytes in RAM then atomically installs."""

    def __init__(self, store: MemoryFileStore, *, hash_algorithm: str) -> None:
        self._store = store
        self._hash_algorithm = hash_algorithm
        self._hasher = hashlib.new(hash_algorithm)
        self._buffer = bytearray()
        self._committed = False
        self._aborted = False
        self._closed = False
        self._commit_stat: BlobStat | None = None  # returned on idempotent commit()

    # ---- AbstractWriter ----

    @property
    def committed(self) -> bool:  # type: ignore[override]
        return self._committed

    def _ensure_open_for_write(self) -> None:
        if self._closed or self._aborted or self._committed:
            raise ValueError("writer is not open for write()")

    def write(self, data: bytes) -> int:
        self._ensure_open_for_write()
        if not data:
            return 0
        self._hasher.update(data)
        self._buffer.extend(data)
        return len(data)

    def commit(self, *, expected_digest: str | None = None) -> BlobStat:
        # Idempotent: if already committed, just return the previous BlobStat
        if self._committed:
            # _commit_stat must be set if _committed is True
            assert self._commit_stat is not None
            return self._commit_stat

        if self._aborted or self._closed:
            raise ValueError("cannot commit after abort/close")

        digest = f"{self._hash_algorithm}:{self._hasher.hexdigest()}"
        if expected_digest is not None and expected_digest != digest:
            # Do not install staged data on mismatch
            raise IntegrityError(f"expected {expected_digest}, computed {digest}")

        data = bytes(self._buffer)

        with self._store._lock:  # type: ignore # pylint: disable=protected-access
            # pylint: disable=protected-access
            existing = self._store._objects.setdefault(digest, data)  # type: ignore
            size = len(
                existing
            )  # if we inserted, existing is `data`; else it’s prior bytes

        stat = BlobStat(digest=digest, size=size, uri=f"mem://{digest}")
        # Mark committed, clear staged data
        self._committed = True
        self._buffer.clear()
        self._commit_stat = stat
        return stat

    def abort(self) -> None:
        # Idempotent; no-op after commit()
        if self._aborted or self._committed:
            return
        self._aborted = True
        self._buffer.clear()

    def close(self) -> None:
        # Safe to call multiple times
        self._closed = True
