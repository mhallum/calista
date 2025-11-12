"""Interface for an index that maps SHA256 hashes to exposure IDs."""

import abc


class ExposureIndex(abc.ABC):
    """Interface for an index that maps SHA256 hashes to exposure IDs.

    This index enforces a one-to-one mapping between SHA256 hashes and exposure IDs.
    This index tracks "active" exposures only; exposures that have been deprecated
    are not included in the index.
    """

    @abc.abstractmethod
    def lookup(self, sha256: str) -> str | None:
        """Lookup the exposure_id by SHA256 hash.

        Args:
            sha256 (str): The SHA256 hash of the exposure file.

        Returns:
            str | None: The exposure_id if found, otherwise None.
        """

    @abc.abstractmethod
    def register(self, sha256: str, exposure_id: str) -> None:
        """Register a new exposure_id with its SHA256 hash.

        Idempotent if the (sha256, exposure_id) pair already exists.

        Args:
            sha256 (str): The SHA256 hash of the exposure file.
            exposure_id (str): The exposure_id to register.

        Raises:
            ExposureIDAlreadyBound: If the sha256 is already registered with a different exposure_id.
            SHA256AlreadyBound: if the exposure_id is already registered with a different sha256.
        """

    @abc.abstractmethod
    def deprecate(self, sha256: str) -> None:
        """Removes the exposure from the index.

        Args:
            sha256 (str): The SHA256 hash of the exposure file to remove.

        Raises:
            SHA256NotFoundError: If the sha256 is not found in the index.
        """
