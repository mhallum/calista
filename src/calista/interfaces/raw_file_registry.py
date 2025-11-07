"""Defines an interface for linking each raw observational FITS file to a single session.

These files are the original, unprocessed image frames captured by the telescope
during observations. Each file is identified by its SHA-256 hash to ensure it
cannot be associated with more than one observation session.
"""

from __future__ import annotations

import abc
from typing import Final


class FileAlreadyRegistered(Exception):
    """Raised when a raw file hash is already bound to a session.

    Attributes:
        sha256: The conflicting SHA-256 hash (lowercase hex).
        existing_session_id: The session currently bound to the hash.
        requested_session_id: The session attempted by the caller.
    """

    def __init__(
        self, sha256: str, existing_session_id: str, requested_session_id: str
    ) -> None:
        super().__init__(
            f"raw file hash {sha256!r} already bound to session "
            f"{existing_session_id!r} (requested {requested_session_id!r})"
        )
        self.sha256 = sha256
        self.existing_session_id = existing_session_id
        self.requested_session_id = requested_session_id


class RawFileRegistry(abc.ABC):
    """Global uniqueness index for raw observation file hashes.

    Purpose:
        Guarantee that every *raw* file recorded at the observatory is associated
        with exactly one observation session. Prevent ingest of the same physical
        FITS file into multiple sessions.

    Scope:
        Applies to all raw frames acquired during a session, including both science
        and calibration exposures such as:
          • bias
          • dark
          • flat (twilight or lamp)
          • arc / wavelength lamp
          • focus, pointing, sky frames, etc.
        Excludes *derived* oxwr combined products (e.g., master bias/dark/flat,
        stacked/processed images, catalogs). Those may be referenced by many
        sessions and follow separate rules or no indexing.

    Rules:
        • Each `sha256` may be bound to at most one `session_id` globally.
        • Repeating the same (sha256, session_id) reservation is idempotent.
        • Binding a `sha256` already associated with another session raises
          `FileAlreadyRegistered`.

    Validation:
        `sha256` MUST be a 64-character lowercase hexadecimal string. Implementations
        MAY normalize to lowercase but MUST reject invalid length or non-hex input.
    """

    HASH_HEX_LEN: Final[int] = 64
    """Length of a SHA-256 lowercase hex digest."""

    # -------- Query --------

    @abc.abstractmethod
    def lookup_session(self, sha256: str) -> str | None:
        """Return the session currently bound to the given hash, if any.

        Args:
            sha256: 64-character lowercase hex SHA-256 of the raw file bytes.

        Returns:
            The `session_id` if the hash is bound, otherwise `None`.

        Raises:
            ValueError: If `sha256` is not valid lowercase hex of length 64.
        """

    # -------- Command --------

    @abc.abstractmethod
    def reserve(self, sha256: str, session_id: str) -> None:
        """Bind a raw file hash to a session (no duplicates allowed).

        Behavior:
            • If `sha256` is unbound, bind it to `session_id`.
            • If already bound to `session_id`, do nothing (idempotent).
            • If bound to a different session, raise FileAlreadyRegistered.

        Args:
            sha256: 64-char lowercase hex SHA-256 of the raw file bytes.
            session_id: Target observation session identifier.

        Raises:
            ValueError: If `sha256` is not valid lowercase hex of length 64.
            FileAlreadyRegistered: If `sha256` is bound to another session.
        """
