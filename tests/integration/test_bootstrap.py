"""Test the bootstrap function."""

import os
from collections.abc import Callable
from unittest import mock

import pytest

from calista.adapters.unit_of_work import SqlAlchemyUnitOfWork
from calista.bootstrap import bootstrap
from calista.bootstrap.bootstrap import (
    build_message_bus,
    build_write_uow,
)
from calista.interfaces.unit_of_work import AbstractUnitOfWork
from calista.service_layer.commands import Command

# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument
# pylint: disable=too-few-public-methods
# pylint: disable=magic-value-comparison


@pytest.fixture()
def setenvvar(monkeypatch):
    """Fixture to set environment variables for tests."""
    with mock.patch.dict(os.environ):
        envvars = {
            "CALISTA_DB_URL": "sqlite:///:memory:",
        }
        for k, v in envvars.items():
            monkeypatch.setenv(k, v)
        yield


class FakeUnitOfWork(AbstractUnitOfWork):
    """A test unit of work for testing purposes."""

    def __init__(self):
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


class CustomCommand(Command):
    """A custom command for testing."""


class TestBuildWriteUoW:
    """Tests for the build_write_uow function."""

    @staticmethod
    def test_build_write_uow_returns_uow():
        """Test that build_write_uow returns a concrete UOW instance."""
        uow = build_write_uow(url="sqlite:///:memory:")
        assert isinstance(uow, SqlAlchemyUnitOfWork)
        assert str(uow.engine.url) == "sqlite:///:memory:"


class TestBuildMessageBus:
    """Tests for the build_message_bus function."""

    @staticmethod
    def test_build_message_bus_injects_uow():
        """Test that build_message_bus injects the unit of work into handlers."""
        uow = FakeUnitOfWork()

        def sample_handler(cmd: Command, uow: FakeUnitOfWork):
            assert uow is not None
            with uow:
                uow.commit()

        command_handlers: dict[type[Command], Callable[..., None]] = {
            Command: sample_handler,
        }

        bus = build_message_bus(uow, command_handlers)
        bus.handle(Command())
        assert hasattr(bus.uow, "committed")
        assert bus.uow.committed is True

    @staticmethod
    def test_forwards_message_to_handler():
        """Test that the message bus forwards messages to the correct handler."""
        uow = FakeUnitOfWork()

        handled_commands = []

        def sample_handler(cmd: CustomCommand, uow: FakeUnitOfWork):
            handled_commands.append(cmd)

        command_handlers: dict[type[Command], Callable[..., None]] = {
            CustomCommand: sample_handler,
        }

        bus = build_message_bus(uow, command_handlers)
        command_instance = CustomCommand()
        bus.handle(command_instance)

        assert len(handled_commands) == 1
        assert handled_commands[0] is command_instance


class TestBootstrap:
    """Tests for the bootstrap function."""

    @staticmethod
    def test_returns_app_container(setenvvar):
        """Test that bootstrap returns an AppContainer instance."""
        app_container = bootstrap()
        assert app_container is not None
        assert app_container.message_bus is not None

    @staticmethod
    def test_returned_message_bus_has_uow(setenvvar):
        """Test that the returned message bus has a unit of work."""
        app_container = bootstrap()
        message_bus = app_container.message_bus
        assert hasattr(message_bus, "uow")
        assert isinstance(message_bus.uow, SqlAlchemyUnitOfWork)
