"""Message bus"""

from collections.abc import Callable

from calista.service_layer import handlers
from calista.service_layer.unit_of_work import AbstractUnitOfWork

# pylint: disable=too-few-public-methods


class MessageBus:
    """Message bus for handling commands

    This class is responsible for dispatching commands to their handlers.
    It acts as central point for communication between different components of the app.
    """

    def __init__(
        self,
        uow: AbstractUnitOfWork,
        command_handlers: dict[type[handlers.commands.Command], Callable[..., None]],
    ):
        self.uow = uow
        self.command_handlers = command_handlers

    def handle(self, message: handlers.commands.Command):
        """Dispatch a message to the appropriate handler."""
        handler = self.command_handlers.get(type(message))
        handler(message)  # type: ignore #FIXME
