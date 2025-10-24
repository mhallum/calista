"""Message bus implementation for handling commands and events."""

import logging
from collections.abc import Callable

from calista.interfaces.unit_of_work import AbstractUnitOfWork

from .commands import Command

logger = logging.getLogger(__name__)

# pylint: disable=too-few-public-methods


class NoHandlerForCommand(LookupError):
    """Exception raised when no handler is found for a command."""

    def __init__(self, cmd: Command) -> None:
        super().__init__(f"No handler found for command {type(cmd).__name__}")


class MessageBus:
    """A simple message bus for handling commands.

    The main responsibility of the message bus is to route commands to their
    appropriate handlers. It also manages logging and error handling during the
    dispatch process. Additionally, it provides access to the unit of work used for
    transactional operations for convenience.

    Args:
        uow: An instance of AbstractUnitOfWork for managing transactional operations.
            This uow should still have been injected into the command handlers, it is
            just also available here for convenience.
        command_handlers: A mapping of command types to their handlers.
            Note that handlers should be callables that accept a single command argument.
            Additional dependencies (i.e. uow) should be injected via closures or other means.

    Note:
        This implementation focuses on command handling and is synchronous for simplicity.
        Event handling, middlewares, and asynchronous dispatch can be integrated later.
        The message bus serves as the main entrypoint to the service layer.
    """

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        command_handlers: dict[type[Command], Callable[..., None]],
    ) -> None:
        self.uow = uow
        self._command_handlers = command_handlers

    def handle(self, cmd: Command) -> None:
        """Handle a command by dispatching it to the appropriate handler.

        Args:
            cmd: The command to handle.

        Raises:
            NoHandlerForCommand: If no handler is found for the command type.
            Exception: If the handler raises an exception.
        """

        if handler := self._command_handlers.get(type(cmd)):
            handler_name = self._get_handler_name(handler)
            logger.debug("Handling command %s with handler %s", cmd, handler_name)
            try:
                handler(cmd)
            except Exception:  # pylint: disable=broad-except
                logger.exception(
                    "Exception handling command %s with handler %s", cmd, handler_name
                )
                raise
        else:
            logger.error("No handler found for command %s", type(cmd).__name__)
            raise NoHandlerForCommand(cmd)

    @staticmethod
    def _get_handler_name(fn: Callable[..., None]) -> str:
        if hasattr(fn, "__name__"):
            return fn.__name__
        if hasattr(fn, "func") and hasattr(fn.func, "__name__"):
            return fn.func.__name__
        return repr(fn)
