"""Module defining Commands."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """Base class for all commands."""
