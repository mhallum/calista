"""Bootstrap the message bus with handlers and unit of work."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from calista import config
from calista.adapters.db.engine import make_engine
from calista.adapters.unit_of_work import SqlAlchemyUnitOfWork
from calista.interfaces.unit_of_work import AbstractUnitOfWork
from calista.service_layer.handlers import COMMAND_HANDLERS
from calista.service_layer.messagebus import MessageBus

if TYPE_CHECKING:
    from calista.service_layer.commands import Command


@dataclass(frozen=True)
class AppContainer:
    """A class to hold application wiring constants."""

    message_bus: MessageBus


def build_write_uow(url: str) -> AbstractUnitOfWork:
    """Build a new unit of work for write operations."""
    engine = make_engine(url)
    return SqlAlchemyUnitOfWork(engine)


def build_message_bus(
    uow: AbstractUnitOfWork, command_handlers: dict[type[Command], Callable[..., None]]
) -> MessageBus:
    """Build a message bus with injected dependencies."""
    dependencies = {"uow": uow}
    injected_command_handlers = {
        command_type: inject_dependencies(handler, dependencies)
        for command_type, handler in command_handlers.items()
    }

    return MessageBus(
        uow,
        command_handlers=injected_command_handlers,
    )


def bootstrap() -> AppContainer:
    """Bootstrap the message bus with handlers and unit of work."""
    uow = build_write_uow(config.get_db_url())
    command_handlers = COMMAND_HANDLERS
    message_bus = build_message_bus(uow, command_handlers)

    return AppContainer(
        message_bus=message_bus,
    )


def inject_dependencies(
    handler: Callable, dependencies: Mapping[str, object]
) -> Callable:
    """Inject dependencies into a handler function based on its parameters."""
    params = inspect.signature(handler).parameters
    deps = {
        name: dependency for name, dependency in dependencies.items() if name in params
    }
    return lambda message: handler(message, **deps)
