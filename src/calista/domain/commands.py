"""commands"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """Base class for all commands."""


@dataclass(frozen=True)
class RegisterImage(Command):
    """Command to register a new image."""

    image_id: str
    session_id: str
    src_path: str
