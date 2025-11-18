"""Local filesystem-based CAS file store adapter."""

import hashlib
import os
import tempfile
from pathlib import Path
from typing import BinaryIO

from calista.interfaces.filestore import BlobStats, FileStore, PathLike

SHA256_LENGTH = 64
CHUNK_SIZE = 1024 * 1024


class LocalFileStore(FileStore):
    """CAS FileStore implementation that uses the local filesystem."""

    def __init__(self, root: PathLike) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    # --- Core Operations ---

    def store(self, fileobj: BinaryIO) -> BlobStats:
        hasher = hashlib.sha256()
        size = 0

        # disable mutmut because it likes to replace False with None,
        # which is falsy and thus equivalent here
        with tempfile.NamedTemporaryFile(dir=self._root, delete=False) as tmp:  # pragma: no mutate # fmt: skip # pylint:disable=line-too-long
            tmp_path = Path(tmp.name)

            for chunk in iter(lambda: fileobj.read(CHUNK_SIZE), b""):
                hasher.update(chunk)
                tmp.write(chunk)
                size += len(chunk)

        sha256 = hasher.hexdigest()
        dest = self._determine_cas_path(sha256)

        # If blob already exists: use it, delete temp
        if dest.exists():
            tmp_path.unlink()
            return BlobStats(size_bytes=size, sha256=sha256)

        # Otherwise atomic move
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp_path, dest)

        return BlobStats(size_bytes=size, sha256=sha256)

    def open_read(self, sha256: str) -> BinaryIO:
        path = self._determine_cas_path(sha256)

        try:
            return path.open("rb")
        except FileNotFoundError:
            raise FileNotFoundError(f"Blob {sha256!r} not found") from None

    # --- Convenience Methods ---

    def exists(self, sha256: str) -> bool:
        path = self._determine_cas_path(sha256)
        return path.is_file()

    # --- Internal Helpers ---

    def _determine_cas_path(self, sha256: str) -> Path:
        """Determine the filesystem path for a given SHA-256 key.

        Sharded directory structure: root/aa/bb/aabbccddeeff...
        """
        self._validate_sha256(sha256)
        return self._root / sha256[0:2] / sha256[2:4] / sha256

    @staticmethod
    def _validate_sha256(sha256: str) -> None:
        """Raise ValueError if the provided SHA-256 key is invalid.

        Enforced:
        - No slashes
        - Exact length of 64 characters
        - Hexadecimal characters only
        """

        if "/" in sha256 or "\\" in sha256:  # pylint: disable=magic-value-comparison
            raise ValueError("Invalid CAS key")

        if len(sha256) != SHA256_LENGTH:
            raise ValueError("Invalid CAS key length (expected 64 characters)")

        try:
            int(sha256, 16)
        except ValueError as e:
            raise ValueError("SHA-256 key contains non-hex characters") from e
