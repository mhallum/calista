"""Module including value objects used across the domain layer."""

from enum import Enum


class FrameType(Enum):
    """Enumeration of possible frame types"""

    BIAS = "bias"
    DARK = "dark"
    FLAT = "flat"
    LIGHT = "light"
