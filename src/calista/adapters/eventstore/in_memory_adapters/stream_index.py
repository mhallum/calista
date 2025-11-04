"""In-memory StreamIndex implementation for testing purposes."""

from calista.interfaces.stream_index import (
    IndexEntrySnapshot,
    NaturalKey,
    NaturalKeyAlreadyBound,
    StreamIdAlreadyBound,
    StreamIndex,
)


class InMemoryStreamIndex(StreamIndex):
    """In-memory StreamIndex implementation for testing purposes.

    Note: This implementation is not thread-safe and is intended
    solely for use in single-threaded test scenarios
    """

    def __init__(self):
        self.index_entries: set[IndexEntrySnapshot] = set()

    # --- lookups ---

    def lookup(self, natural_key: NaturalKey) -> IndexEntrySnapshot | None:
        for entry in self.index_entries:
            if entry.natural_key == natural_key:
                return entry
        return None

    def _lookup_by_stream(self, stream_id: str) -> IndexEntrySnapshot | None:
        for entry in self.index_entries:
            if entry.stream_id == stream_id:
                return entry
        return None

    # --- version updates ---

    def update_version(self, stream_id: str, version: int) -> None:
        entry_to_update = None
        for entry in self.index_entries:
            if entry.stream_id == stream_id:
                entry_to_update = entry
                break
        if entry_to_update is not None and version > entry_to_update.version:
            self.index_entries.remove(entry_to_update)
            self.index_entries.add(
                IndexEntrySnapshot(
                    natural_key=entry_to_update.natural_key,
                    stream_id=entry_to_update.stream_id,
                    version=version,
                )
            )

    # --- reservations ---

    def reserve(self, natural_key: NaturalKey, stream_id: str) -> None:
        # idempotency check
        natural_key_entry = self.lookup(natural_key)
        stream_id_entry = self._lookup_by_stream(stream_id)
        if natural_key_entry == stream_id_entry and natural_key_entry is not None:
            return

        # existing bindings checks
        if natural_key_entry is not None:
            raise NaturalKeyAlreadyBound(
                natural_key=natural_key.key,
                stream_id=natural_key_entry.stream_id,
                kind=natural_key.kind,
            )
        if stream_id_entry is not None:
            raise StreamIdAlreadyBound(
                stream_id=stream_id,
                natural_key=stream_id_entry.natural_key.key,
                kind=stream_id_entry.natural_key.kind,
            )

        # no conflicts, create new binding
        self.index_entries.add(
            IndexEntrySnapshot(natural_key=natural_key, stream_id=stream_id, version=0)
        )
