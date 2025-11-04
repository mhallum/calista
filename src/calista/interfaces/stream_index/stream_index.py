"""Interfaces for mapping natural keys to event stream identifiers.

Defines the `StreamIndex` abstraction used to bind human-readable natural keys
to immutable stream IDs (ULIDs or UUIDs). Supports idempotent reservation,
lookup, and monotonic version fencing for event-sourced aggregates.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass(frozen=True)
class NaturalKey:
    """Opaque, structured natural key for a stream."""

    kind: str  # e.g. "observation_session"
    key: str  # canonicalized string, e.g. "LDT-20240621-LMI-S001"


@dataclass(frozen=True)
class IndexEntrySnapshot:
    """Index row describing the binding from natural key → stream id."""

    natural_key: NaturalKey
    stream_id: str  # ULID/UUID
    version: int  # last event version observed for this stream


class StreamIndex(abc.ABC):
    """Natural-key → stream id lookup with idempotent reservation & version fencing."""

    @abc.abstractmethod
    def lookup(self, natural_key: NaturalKey) -> IndexEntrySnapshot | None:
        """Retrieve the existing mapping for a natural key.

        Looks up the index entry associated with the given natural key.
        If the key is not present in the index, returns ``None``.

        Args:
            natural_key: The structured natural key to look up.

        Returns:
            IndexEntry | None: The existing mapping if found, otherwise ``None``.
        """

    @abc.abstractmethod
    def reserve(self, natural_key: NaturalKey, stream_id: str) -> None:
        """Reserve a natural key for a given stream ID.

        Creates a new mapping from the natural key to the stream ID if none exists.
        If the natural key is already bound to the same stream ID, the call is
        idempotent. If it is bound to a different stream ID, a
        ``NaturalKeyAlreadyBound`` exception is raised.

        Args:
            natural_key: The structured natural key to reserve.
            stream_id: The ULID or UUID identifying the event stream.

        Raises:
            NaturalKeyAlreadyBound: If the natural key is already associated with a
                different stream ID.
            StreamIdAlreadyBound: If the stream ID is already associated with a
                different natural key.
        """

    @abc.abstractmethod
    def update_version(self, stream_id: str, version: int) -> None:
        """Advance the stored version fence for a stream.

        Updates the version number for the specified stream if the provided
        version is greater than the currently stored value. The version fence
        is monotonic—once advanced, it cannot move backward. If the stream
        does not exist in the index, this operation is a no-op.

        Args:
            stream_id: The ULID or UUID identifying the event stream.
            version: The new version number to record.
        """
