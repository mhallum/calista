"""Unit tests for the MessageBus"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

import pytest

from calista.interfaces.unit_of_work import AbstractUnitOfWork
from calista.service_layer.commands import Command
from calista.service_layer.messagebus import MessageBus, NoHandlerForCommand

# pylint: disable=unused-argument, too-few-public-methods


# --- Fakes ---


class FakeUoW(AbstractUnitOfWork):
    """A fake unit of work for testing purposes."""

    def commit(self):
        """Fake commit method."""

    def rollback(self):
        """Fake rollback method."""


@dataclass(frozen=True)
class CommandA(Command):
    """A simple fake command for testing purposes."""

    x: int = 0


@dataclass(frozen=True)
class CommandB(Command):
    """A simple fake command for testing purposes."""

    msg: str = "hi"


# --- Assert Helpers ---


def assert_log_message(records, message, level: str) -> None:
    """Assert that a log message is in the log records."""
    log_msgs = [rec.getMessage() for rec in records if rec.levelname == level]
    assert message in log_msgs


# --- Tests ---


def test_dispatches_to_specific_handler_once(caplog):
    """Test that MessageBus dispatches to the correct handler once.
    and that it logs the handling action.
    """

    calls: list[Command] = []

    def handle_a(cmd: CommandA) -> None:
        calls.append(cmd)

    def handle_b(cmd: CommandB) -> None:
        calls.append(cmd)

    bus = MessageBus(
        FakeUoW(), command_handlers={CommandA: handle_a, CommandB: handle_b}
    )
    a = CommandA(42)

    with caplog.at_level("DEBUG"):
        bus.handle(a)

    # Assert that proper handler was called once
    assert calls == [a]

    # Assert that log contains handling message
    assert_log_message(
        caplog.records,
        f"Handling command {a} with handler {handle_a.__name__}",
        "DEBUG",
    )


def test_message_bus_no_handler_logs_error(caplog):
    """Test that MessageBus logs an error and raises when no handler is found."""
    bus = MessageBus(FakeUoW(), command_handlers={})
    with caplog.at_level("ERROR"):
        with pytest.raises(
            NoHandlerForCommand,
            match="No handler found for command CommandA",
        ):
            cmd = CommandA()
            bus.handle(cmd)

    assert_log_message(
        caplog.records,
        "No handler found for command CommandA",
        "ERROR",
    )


def test_message_bus_handler_exception_logs(caplog):
    """Test that MessageBus logs an exception raised by a handler and reraises."""

    def faulty_handler(cmd: CommandA):
        raise RuntimeError("Handler error")

    handlers: dict[type[Command], Callable[..., None]] = {
        CommandA: faulty_handler,
    }

    bus = MessageBus(FakeUoW(), command_handlers=handlers)
    with caplog.at_level("ERROR"):
        with pytest.raises(RuntimeError):
            cmd = CommandA()
            bus.handle(cmd)
    assert_log_message(
        caplog.records,
        f"Exception handling command {cmd} with handler {faulty_handler.__name__}",
        "ERROR",
    )


def test_handler_name_falls_back_to_repr(caplog):
    """Test that handler name is correctly extracted when __name__ is missing."""

    class CallableObj:
        """A callable object without a __name__ attribute."""

        def __call__(self, x):
            pass

    bus = MessageBus(FakeUoW(), command_handlers={CommandA: CallableObj()})
    with caplog.at_level("DEBUG"):
        bus.handle(cmd=CommandA())
    logs = " ".join(rec.message for rec in caplog.records)
    pattern = r"Handling command CommandA\(x=0\) with handler <.*>"
    assert re.search(pattern, logs), f"Expected log pattern not found: {pattern}"


def test_handler_name_with_closure(caplog):
    """Test that handler name is correctly extracted from a closure."""

    def record_handler(cmd: CommandA, sink: list[CommandA]) -> None:
        """Test handler that records commands to a sink."""
        sink.append(cmd)

    sink: list[CommandA] = []
    injected_handler = partial(record_handler, sink=sink)
    bus = MessageBus(FakeUoW(), command_handlers={CommandA: injected_handler})
    with caplog.at_level("DEBUG"):
        cmd = CommandA(0)
        bus.handle(cmd)
    assert sink == [cmd]
    assert_log_message(
        caplog.records,
        f"Handling command {cmd} with handler {injected_handler.func.__name__}",  # pylint: disable=no-member
        "DEBUG",
    )


def test_message_bus_exposes_uow():
    """Test that MessageBus exposes the unit of work instance."""
    uow = FakeUoW()
    bus = MessageBus(uow, command_handlers={})
    assert bus.uow is uow
