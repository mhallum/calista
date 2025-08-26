"""Content-Addressed File Store (CAS) interface.

This module defines a minimal, backend-agnostic interface for storing and
retrieving immutable blobs addressed **only** by their content digest
(`"<algorithm>:<hex>"`, e.g., `"sha256:…"`)—no path/alias semantics live here.



Key concepts:
    - **Pure CAS**: Identity is the digest; the store is oblivious to paths/names.
    - **Separation of concerns**: Any aliasing/index of `(namespace, relpath) → digest`
        belongs in a *projection* (e.g., a DB table) outside this module.
    - **Safety**: Writers are leak-safe. Leaving a `with` block without `commit()`
        discards staged bytes (via `abort()`) and closes handles.
    - **Idempotency**: `commit()` SHOULD be idempotent—if the computed digest already
        exists, return the existing `BlobStat` instead of raising.
    - **Performance**: `stat()` MUST NOT read blob bodies and MAY omit size if it’s
        expensive. `open_read()` returns a stream for efficient, chunked access.


Public API:
    - Exceptions: `FileStoreError`, `NotFound`, `ReadOnlyError`, `IntegrityError`
    - Data types: `BlobStat`
    - Abstract interfaces: `AbstractWriter`, `AbstractFileStore`

Typical usage:
    ```py
    info = store.put_path("raw/image.fits")
    with store.open_read(info.digest) as fp:
        head = fp.read(1024)
    ```

Durability and concurrency:
    - `open_write(fsync=True)` requests durable placement on `commit()`.
    - Implementations should use atomic placement (e.g., temp + `os.replace`).
    - `commit()` and `abort()` must be idempotent.

"""

import abc
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import BinaryIO

_CHUNK = 1024 * 1024  # 1 MiB


class FileStoreError(Exception):
    """Base class for all file-store errors."""


class NotFound(FileStoreError):
    """Requested digest is absent from the store."""


class ReadOnlyError(FileStoreError):
    """A mutating operation was attempted on a read-only store."""


class IntegrityError(FileStoreError):
    """Digest/content mismatch or integrity violation detected."""


@dataclass(frozen=True)
class BlobStat:
    """Minimal blob descriptor from the CAS.

    Attributes:
        digest: Content identity in the form ``"<algorithm>:<hex>"``, e.g. ``"sha256:..."``.
        size: Size in bytes if cheaply known; may be ``None`` for expensive backends.
        uri: Optional locator hint (e.g., ``"file:///..."``). Never the identity.
    """

    digest: str
    size: int | None = None
    uri: str | None = None


class AbstractWriter(abc.ABC):
    """Write handle that atomically commits content into the CAS.

    Typical lifecycle:
        1. Obtain via `open_write`.
        2. Call `write` zero or more times.
        3. Finalize with `commit` *or* discard with `abort`.
        4. Always `close` (use as a context manager when possible).
    """

    @property
    @abc.abstractmethod
    def committed(self) -> bool:
        """Return True if the object has been committed."""

    @abc.abstractmethod
    def write(self, data: bytes) -> int:
        """Append bytes to the staged blob.

        Args:
            data (bytes): Byte chunk to append.

        Returns:
            int: Number of bytes written (typically ``len(data)``).

        Raises:
            ValueError: If called after `commit()`/`abort()`/`close()`.
            OSError: Underlying I/O errors.
        """

    @abc.abstractmethod
    def commit(self, *, expected_digest: str | None = None) -> BlobStat:
        """Finalize the staged bytes and install the blob in the CAS.

         The implementation must compute the digest over the exact bytes written.
         If ``expected_digest`` is provided, it must match the computed digest.

        Args:
             expected_digest: Optional guard of the form ``"<algorithm>:<hex>"``.

         Returns:
             A ``BlobStat`` describing the committed blob. ``size`` should be set when
             cheap; ``uri`` may be provided as a locator hint.

         Raises:
             IntegrityError: If ``expected_digest`` does not match the computed digest.
             OSError: Underlying I/O errors.

         Notes:
             Implementations should be idempotent. If the blob already exists, discard
             staged data and return the existing blob’s ``BlobStat``.
        """

    @abc.abstractmethod
    def abort(self) -> None:
        """Discard staged content and remove any temporary artifacts.

        Must be idempotent; calling after ``commit()`` is a no-op.
        """

    @abc.abstractmethod
    def close(self) -> None:
        """Release resources associated with the writer.

        Safe to call multiple times. Writers used as context managers MUST call
        ``abort()`` on exceptions unless ``commit()`` already ran.
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
    """Pure CAS interface.

    Identity is the digest; blobs are immutable.
    """

    @abc.abstractmethod
    def open_write(self, *, fsync: bool = True) -> AbstractWriter:
        """Return a write handle for staging a new object.

        Args:
            fsync (bool): If ``True``, the implementation SHOULD ensure durable placement
                on commit (e.g., fsync parent directory on POSIX).
                Defaults to `True`.

        Returns:
            AbstractWriter: Use to `write()` then `commit()` bytes.

        Raises:
            OSError: Underlying I/O errors.
        """

    @abc.abstractmethod
    def open_read(self, digest: str) -> BinaryIO:
        """Open a read-only byte stream for the blob identified by `digest`.

        Args:
            digest (str): Content digest ``"<algorithm>:<hex>"``.

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
            digest (str): Content digest ``"<algorithm>:<hex>"``.

        Returns:
            BlobStat: Minimal descriptor for the stored blob.

        Raises:
            NotFound: If the digest is not present.
        """

    # --- Convenience methods (non-abstract) ---

    def exists(self, digest: str) -> bool:
        """Return ``True`` if an object with ``digest`` is present.

        Args:
            digest: Content digest ``"<algorithm>:<hex>"``.

        Returns:
            ``True`` if present, otherwise ``False``.
        """
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

        Notes:
            `commit()` should be idempotent: if the blob already exists, the method
            should return the existing blob’s metadata.
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
        """Ingest an in-memory byte string into the CAS.

        Args:
            data: The bytes to store.
            fsync: If ``True``, request durability on commit.
            expected_digest: Optional guard (``"<algorithm>:<hex>"``) verified on commit.

        Returns:
            The committed blob’s :class:`BlobStat`.
        """
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

        Args:
            stream: Open binary stream to read from.
            fsync: If ``True``, request durability on commit.
            expected_digest: Optional guard (``"<algorithm>:<hex>"``) verified on commit.
            chunk_size: Read size per iteration (bytes).

        Returns:
            The committed blob’s :class:`BlobStat`.
        """

        with self.open_write(fsync=fsync) as w:
            for chunk in iter(lambda: stream.read(chunk_size), b""):
                w.write(chunk)
            return w.commit(expected_digest=expected_digest)

    def readall(self, digest: str) -> bytes:
        """Read the entire object into memory (convenience).

        Args:
            digest: Content digest ``"<algorithm>:<hex>"``.

        Returns:
            The full blob bytes.
        """
        with self.open_read(digest) as fp:
            return fp.read()
