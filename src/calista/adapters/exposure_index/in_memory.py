"""In-memory implementation of the ExposureIndex interface."""

from calista.interfaces.exposure_index import ExposureIndex
from calista.interfaces.exposure_index.errors import (
    ExposureIDAlreadyBound,
    ExposureIDNotFoundError,
    SHA256AlreadyBound,
)


class InMemoryExposureIndex(ExposureIndex):
    """In-memory implementation of the ExposureIndex interface.

    This implementation is intended for testing and development purposes only.
    It does not persist data and is not suitable for production use.
    """

    def __init__(self) -> None:
        self._index: dict[str, str] = {}  # sha256: exposure_id

    def lookup(self, sha256: str) -> str | None:
        return self._index.get(sha256)

    def register(self, sha256: str, exposure_id: str) -> None:
        if self._index.get(sha256) is not None:
            if self._index[sha256] != exposure_id:
                raise SHA256AlreadyBound(sha256, self._index[sha256])
            return  # idempotent
        if exposure_id in self._index.values():
            # Find the sha256 that is already bound to this exposure_id
            bound_sha256 = next(
                key for key, value in self._index.items() if value == exposure_id
            )
            raise ExposureIDAlreadyBound(exposure_id, bound_sha256)
        self._index[sha256] = exposure_id

    def deprecate(self, exposure_id: str) -> None:
        if exposure_id not in self._index.values():
            raise ExposureIDNotFoundError(exposure_id=exposure_id)

        # Find the sha256 that is bound to this exposure_id
        bound_sha256 = next(
            key for key, value in self._index.items() if value == exposure_id
        )

        del self._index[bound_sha256]
