"""Test suite for edge cases in the message bus."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from calista.bootstrap import bootstrap
from calista.domain.commands import Command
from calista.service_layer.messagebus import (
    HandlingException,
    MessageBus,
    MissingHandlerError,
)

from .test_handlers import FakeFileStore, FakeUnitOfWork

if TYPE_CHECKING:
    from logging import LogRecord

    from calista.adapters.filestore import AbstractFileStore
    from calista.service_layer.unit_of_work import AbstractUnitOfWork


@dataclass(frozen=True)
class FakeCommand(Command):
    """A fake command for testing."""


def failing_command_handler(command: FakeCommand):
    """A handler that raises an exception."""
    raise Exception("Simulated failure")  # pylint: disable=broad-exception-raised


def assert_logged(
    record: "LogRecord", message: str, level: str, traceback: bool = False
):
    """Assert that a log record contains the expected message and level."""
    assert record.message == message, f"Expected log message not found: {message}"

    assert record.levelname == level, (
        f"Expected log level {level} but got {record.levelname}"
    )

    if traceback:
        # Ensure that the record has an exception info if traceback is expected
        assert record.exc_info is not None, "Expected a traceback to be logged"


def bootstrap_test_app(
    uow: "AbstractUnitOfWork" = FakeUnitOfWork(),
    files: "AbstractFileStore" = FakeFileStore(Path("fake_files")),
    command_handlers: dict[type[Command], Callable[..., None]] | None = None,
) -> MessageBus:
    """Bootstrap a test instance of the MessageBus."""
    return bootstrap(uow=uow, files=files, command_handlers=command_handlers)


class TestCommandHandlingEdgeCases:
    """Test suite for edge cases in command handling."""

    @staticmethod
    def test_bus_logs_and_raises_error_on_missing_handler(
        caplog: pytest.LogCaptureFixture,
    ):
        """Verify that the message bus logs an error and raises a `MissingHandlerError`
        when attempting to handle a command with no registered handler.
        """

        bus = bootstrap_test_app()

        command = FakeCommand()
        expected_content = "No handler found for command: FakeCommand"
        expected_level = "ERROR"

        with caplog.at_level(expected_level):
            with pytest.raises(MissingHandlerError, match=expected_content):
                bus.handle(command)

        assert_logged(caplog.records[-1], expected_content, expected_level)

    @staticmethod
    def test_bus_logs_and_raises_error_on_unexpected_error(
        caplog: pytest.LogCaptureFixture,
    ):
        """Verify that the message bus logs and raises a `HandlingException` when a
        command handler raises an unexpected error.
        """
        bus = bootstrap_test_app(
            command_handlers={FakeCommand: failing_command_handler},
        )

        command = FakeCommand()

        expected_level = "ERROR"
        expected_content = (
            "Unexpected error occurred while handling command: FakeCommand()"
        )

        with caplog.at_level(expected_level):
            with pytest.raises(HandlingException, match=expected_content):
                bus.handle(command)

        assert_logged(
            caplog.records[-1], expected_content, expected_level, traceback=True
        )
