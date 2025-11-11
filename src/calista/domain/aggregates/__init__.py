"""Aggregates package.


All aggregates are defined in this package and inherit from the base `Aggregate`
class in `base.py`. They are re-exported here to provide a single, convenient
import path.
"""

from .base import Aggregate
from .observation_session import ObservationSession

__all__ = ["Aggregate", "ObservationSession"]
