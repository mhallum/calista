"""Aggregates package.


All aggregates are defined in this package and inherit from the base `Aggregate`
class in `base.py`. They are re-exported here to provide a single, convenient
import path.
"""

from .base import Aggregate
from .observation_session import ObservationSession
from .raw_fits_file import RawFitsFile

__all__ = ["Aggregate", "ObservationSession", "RawFitsFile"]
