"""Service layer handlers."""

from collections.abc import Callable

COMMAND_HANDLERS: dict[type, Callable[..., None]] = {}
