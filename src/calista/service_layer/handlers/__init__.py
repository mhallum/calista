"""Service layer handlers."""

from collections.abc import Callable

from .catalog_handlers import COMMAND_HANDLERS as CATALOG_COMMAND_HANDLERS
from .observation_session_handlers import (
    COMMAND_HANDLERS as OBS_SESSION_COMMAND_HANDLERS,
)

__all__ = ["COMMAND_HANDLERS"]

COMMAND_HANDLERS: dict[type, Callable[..., None]] = {
    **CATALOG_COMMAND_HANDLERS,
    **OBS_SESSION_COMMAND_HANDLERS,
}
