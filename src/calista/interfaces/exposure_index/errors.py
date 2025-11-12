"""Errors raised by the ExposureIndex."""


class ExposureIndexError(Exception):
    """Base class for ExposureIndex errors."""


class SHA256AlreadyBound(ExposureIndexError):
    """Raised when the ExposureIndex is asked to bind a SHA256 that
    is already bound to a different exposure ID.

    Attributes:
        sha256 (str): The SHA256 hash that is already bound.
        exposure_id (str): The exposure ID that the SHA256 is bound to.
    """

    def __init__(self, sha256: str, exposure_id: str):
        super().__init__(
            f"SHA256 '{sha256}' is already bound to exposure ID '{exposure_id}'."
        )
        self.sha256 = sha256
        self.exposure_id = exposure_id


class ExposureIDAlreadyBound(ExposureIndexError):
    """Raised when the ExposureIndex is asked to bind an exposure ID that
    is already bound to a different SHA256 hash.

    Attributes:
        exposure_id (str): The exposure ID that is already bound.
        sha256 (str): The SHA256 hash that the exposure ID is bound to.
    """

    def __init__(self, exposure_id: str, sha256: str):
        super().__init__(
            f"Exposure ID '{exposure_id}' is already bound to SHA256 '{sha256}'."
        )
        self.exposure_id = exposure_id
        self.sha256 = sha256


class ExposureIDNotFoundError(ExposureIndexError):
    """Raised when the ExposureIndex is asked to deprecate an exposure whose id
    is not found in the index.

    Attributes:
        exposure_id (str): The exposure ID that was not found.
    """

    def __init__(self, exposure_id: str):
        super().__init__(f"Exposure ID '{exposure_id}' not found in ExposureIndex.")
        self.exposure_id = exposure_id
