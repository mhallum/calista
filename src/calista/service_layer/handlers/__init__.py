"""Service layer handlers."""

from collections.abc import Callable

from .catalog_handlers import COMMAND_HANDLERS as CATALOG_COMMAND_HANDLERS

COMMAND_HANDLERS: dict[type, Callable[..., None]] = {**CATALOG_COMMAND_HANDLERS}
