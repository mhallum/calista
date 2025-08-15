"""Message bus for handling commands in the CALISTA pipeline"""

import logging
from collections.abc import Callable

from calista.domain import commands
from calista.service_layer import handlers
from calista.service_layer.unit_of_work import AbstractUnitOfWork

# pylint: disable=too-few-public-methods

logger = logging.getLogger(__name__)


class MissingHandlerError(Exception):
    """Exception raised when a command handler is missing."""

    def __init__(self, command: commands.Command, message: str | None = None):
        if message is None:
            message = f"No handler found for command: {command.__class__.__name__}"
        super().__init__(message)


class HandlingException(Exception):
    """Exception raised when an unexpected error occurs while handling a command."""

    def __init__(self, command: commands.Command, message: str | None = None):
        if message is None:
            message = f"Unexpected error occurred while handling command: {command}"
        super().__init__(message)


class MessageBus:
    """Message bus for handling commands

    This class is responsible for dispatching commands to their handlers.
    """

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        command_handlers: dict[
            type[handlers.commands.Command], Callable[[commands.Command], None]
        ],
    ):
        self.uow = uow
        self.command_handlers = command_handlers

    def handle(self, command: commands.Command) -> None:
        """Dispatch a command to its registered handler.

        Args:
            command (Command): The command to be handled

        Raises:
            MissingHandlerError: If no handler is registered for this command type.
            HandlingException: If an unhandled exception occurs during execution.
        """

        logger.debug("Handling command: %s", command)

        try:
            self._handle_command(command)
        except MissingHandlerError as e:
            logger.error(e.args[0])
            raise e
        except HandlingException as e:
            logger.exception(e.args[0])
            raise e

    def _handle_command(self, command: commands.Command) -> None:
        """Invoke the registered handler for the specified command.

        Args:
            command (Command): The command instance to process.

        Raises:
            MissingHandlerError: If no handler is registered for this command type.
            HandlingException: If an unhandled exception occurs during execution.
        """

        try:
            handler = self.command_handlers[type(command)]
        except KeyError as e:
            raise MissingHandlerError(command) from e

        try:
            handler(command)
        except Exception as e:
            raise HandlingException(command) from e
