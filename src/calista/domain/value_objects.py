"""Module including value objects used across the domain layer."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class FrameType(Enum):
    """Enumeration of possible frame types"""

    BIAS = "bias"
    DARK = "dark"
    FLAT = "flat"
    LIGHT = "light"


@dataclass(frozen=True)
class StoredFileMetadata:
    """Value object representing metadata of a stored file."""

    sha256: str
    cas_key: str
    size_bytes: int
    stored_at: datetime
