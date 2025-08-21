"""Content-Addressed File Store (CAS) interface.

This module defines a minimal, backend-agnostic interface for storing and
retrieving immutable blobs addressed **only** by their content digest
(`"<algorithm>:<hex>"`, e.g., `"sha256:…"`)—no path/alias semantics live here.

Exports
-------
Exceptions
    - FileStoreError: Base class for store errors.
    - NotFound:       Requested digest is absent.
    - AlreadyExists:  (Optional) Used by implementations that reject duplicates.
    - ReadOnlyError:  Mutating operation attempted on a read-only store.
    - IntegrityError: Digest/content mismatch or integrity violation.

Data types
    - BlobStat: Minimal, cheap metadata about a blob (`digest`, optional `size`,
      optional `uri` locator hint). Returned by `stat()` and `commit()`.

Abstract interfaces
    - AbstractWriter: Stages bytes for a single blob; `write()`, `commit()`,
      `abort()`, `close()`. Usable as a context manager.
    - AbstractFileStore: Opens writers/readers and exposes `stat()` plus a few
      convenience helpers (`exists()`, `put_*()`, `readall()`).

Design goals
------------
- **Pure CAS**: Identity is the digest; the store is oblivious to paths/names.
- **Separation of concerns**: Any aliasing/index of `(namespace, relpath) → digest`
  belongs in a *projection* (e.g., a DB table) outside this module.
- **Safety**: Writers are leak-safe. Leaving a `with` block without `commit()`
  discards staged bytes (via `abort()`) and closes handles.
- **Idempotency**: `commit()` SHOULD be idempotent—if the computed digest already
  exists, return the existing `BlobStat` instead of raising.
- **Performance**: `stat()` MUST NOT read blob bodies and MAY omit size if it’s
  expensive. `open_read()` returns a stream for efficient, chunked access.

Durability & concurrency
------------------------
- `open_write(fsync=True)` signals that the implementation SHOULD make a best-effort
  to durably install the blob on `commit()` (e.g., `fsync` file and parent dir on POSIX).
- Implementations SHOULD use atomic placement (e.g., write to a temp file and
  `os.replace` into the content path).
- `abort()` and `commit()` MUST be idempotent; `abort()` MUST be a no-op after `commit()`.

Typical usage
-------------
Ingest a local file:

    info = store.put_path("raw/image.fits")
    print(info.digest, info.size)

Stream arbitrary bytes:

    with store.open_write() as w:
        for chunk in producer():
            w.write(chunk)
        info = w.commit()

Read and inspect:

    if store.exists(info.digest):
        meta = store.stat(info.digest)
        with store.open_read(info.digest) as fp:
            head = fp.read(1024)

Notes
-----
- `open_read()` returns a file-like object; the **caller** must close it.
- `BlobStat.uri` is a *hint* (e.g., `"file:///…"`); it is never the identity.
- Digest strings are case-sensitive by convention; implementations MAY normalize
  per algorithm rules (e.g., lower-case hex).

This interface is intentionally small to make implementing alternative backends
(local filesystem, object stores, memory, etc.) straightforward and testable.
"""

import abc
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import BinaryIO

_CHUNK = 1024 * 1024  # 1 MiB


class FileStoreError(Exception):
    """Raised when there is a file store error."""


class NotFound(FileStoreError):
    """Raised when a file is not found in the store."""


class ReadOnlyError(FileStoreError):
    """Raised when a file store is read-only."""


class IntegrityError(FileStoreError):
    """Raised when there is an integrity error in the file store."""


@dataclass(frozen=True)
class BlobStat:
    """Minimal blob descriptor from the CAS.

    Attributes:
        digest: Content identity in the form "<algorithm>:<hex>", e.g. "sha256:...".
        size: Size in bytes if cheaply known; may be None for expensive backends.
        uri: Optional locator hint (e.g., "file:///..."); never the identity.
    """

    digest: str
    size: int | None = None
    uri: str | None = None


class AbstractWriter(abc.ABC):
    """Write handle that atomically commits content into the CAS.

    Typical lifecycle:
      1) Obtain via `AbstractFileStore.open_write()`
      2) `write()` bytes 0..N times
      3) `commit()` to finalize, or `abort()` to discard
      4) Always `close()` (use as a context manager when possible)
    """

    @property
    @abc.abstractmethod
    def committed(self) -> bool:
        """Return True if the object has been committed."""

    @abc.abstractmethod
    def write(self, data: bytes) -> int:
        """Append bytes to the pending object.

        Args:
            data: Byte chunk to append.

        Returns:
            int: Number of bytes written (typically `len(data)`).

        Raises:
            ValueError: If called after `commit()`/`abort()`/`close()`.
            OSError: Underlying I/O errors.
        """

    @abc.abstractmethod
    def commit(self, *, expected_digest: str | None = None) -> BlobStat:
        """Finalize the object and install it into the CAS.

        The implementation MUST compute the digest over the exact bytes written.
        If `expected_digest` is provided, it MUST match the computed digest.


        Idempotency:
            Implementations SHOULD be idempotent. If the computed digest already
            exists, they SHOULD discard staged data and return the existing
            object's `BlobStat` rather than raise.

        Args:
            expected_digest: Optional guard of the form "<algorithm>:<hex>".

        Returns:
            BlobStat: Includes the computed `digest`. `size` SHOULD be set when
            cheap; `uri` MAY be provided as a locator hint.

        Raises:
            IntegrityError: If `expected_digest` is provided and does not match.
            OSError: Underlying I/O errors.
        """

    @abc.abstractmethod
    def abort(self) -> None:
        """Discard buffered content and remove temp artifacts.

        Idempotent: multiple calls MUST NOT raise, and is no-op after commit().
        """

    @abc.abstractmethod
    def close(self) -> None:
        """Release resources associated with the writer.

        Safe to call multiple times. Writers used as context managers MUST call
        `abort()` on exceptions unless `commit()` already ran.
        """

    def __enter__(self) -> "AbstractWriter":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            self.abort()
        finally:
            self.close()


class AbstractFileStore(abc.ABC):
    """Pure CAS. Identity is the digest."""

    @abc.abstractmethod
    def open_write(self, *, fsync: bool = True) -> AbstractWriter:
        """Return a write handle for staging a new object.

        Args:
            fsync: If True, the implementation SHOULD ensure durable placement
                on commit (e.g., fsync parent directory on POSIX).

        Returns:
            AbstractWriter: Use to `write()` then `commit()` bytes.

        Raises:
            OSError: Underlying I/O errors.
        """

    @abc.abstractmethod
    def open_read(self, digest: str) -> BinaryIO:
        """Open a read-only byte stream for the object identified by `digest`.

        Args:
            digest: Content digest "<algorithm>:<hex>".

        Returns:
            BinaryIO: Readable (and ideally seekable) stream at offset 0.

        Raises:
            NotFound: If the digest is not present.
            OSError: Underlying I/O errors.
        """

    @abc.abstractmethod
    def stat(self, digest: str) -> BlobStat:
        """Return cheap metadata for `digest` or raise if missing.

        Must not read the blob body. MAY return `size=None` if costly.

        Args:
            digest: Content digest "<algorithm>:<hex>".

        Returns:
            BlobStat: Minimal descriptor for the stored blob.

        Raises:
            NotFound: If the digest is not present.
        """

    # --- Convenience methods (non-abstract) ---

    def exists(self, digest: str) -> bool:
        """Return True if an object with `digest` is present."""
        try:
            self.stat(digest)
        except NotFound:
            return False

        return True

    def put_path(  # pylint: disable=too-many-arguments
        self,
        src: str | Path,
        *,
        fsync: bool = True,
        expected_digest: str | None = None,
        chunk_size: int = _CHUNK,
        follow_symlinks: bool = False,
    ) -> BlobStat:
        """Stream a local file into the CAS and return its metadata.

        This is a convenience wrapper around `open_write()` that:
        - streams the file (no read-all-into-RAM),
        - computes the digest during the write,
        - commits atomically, and
        - returns BlobStat.

        Args:
            src: Path to a local file to ingest.
            fsync: If True, request durability on commit.
            expected_digest: Optional guard ("<algorithm>:<hex>"). If provided,
                commit MUST verify equality and fail on mismatch.
            chunk_size: Read size per iteration (bytes).
            follow_symlinks: If False (default), refuse symlinks.

        Returns:
            BlobStat: minimal metadata including computed digest.

        Raises:
            FileNotFoundError: If `src` does not exist.
            IsADirectoryError: If `src` is a directory.
            ValueError: If `src` is a symlink and `follow_symlinks=False`.
            IntegrityError: If `expected_digest` mismatches computed digest.
            OSError: For underlying I/O errors.
        """
        src_path = Path(src)

        if not follow_symlinks and src_path.is_symlink():
            raise ValueError(f"Refusing symlink: {src_path}")

        if not src_path.is_file():
            # Maintain clear diagnostics: distinguish missing vs directory.
            if not src_path.exists():
                raise FileNotFoundError(src_path)
            raise IsADirectoryError(src_path)

        with self.open_write(fsync=fsync) as w, src_path.open("rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                w.write(chunk)
            # Commit MUST be idempotent: if blob already exists, return its info.
            return w.commit(expected_digest=expected_digest)

    def put_bytes(
        self, data: bytes, *, fsync: bool = True, expected_digest: str | None = None
    ) -> BlobStat:
        """Ingest an in-memory byte string into the CAS."""
        with self.open_write(fsync=fsync) as w:
            if data:
                w.write(data)
            return w.commit(expected_digest=expected_digest)

    def put_stream(
        self,
        stream: BinaryIO,
        *,
        fsync: bool = True,
        expected_digest: str | None = None,
        chunk_size: int = _CHUNK,
    ) -> BlobStat:
        """Ingest from an already-open binary stream into the CAS.

        The stream is consumed until EOF and is **not** closed by this method.
        """
        with self.open_write(fsync=fsync) as w:
            for chunk in iter(lambda: stream.read(chunk_size), b""):
                w.write(chunk)
            return w.commit(expected_digest=expected_digest)

    def readall(self, digest: str) -> bytes:
        """Read the entire object into memory (convenience)."""
        with self.open_read(digest) as fp:
            return fp.read()
