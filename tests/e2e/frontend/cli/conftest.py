"""Fixtures and test helpers for end-to-end CLI logging tests.

Provides a test-only `log-demo` Click command that emits structured log
messages, plus fixtures to register that command, obtain a CliRunner, and
run tests within an isolated filesystem.
"""

import logging

import click
import pytest
from click.testing import CliRunner

from calista.entrypoints.cli.main import calista

# pylint: disable=redefined-outer-name


@click.command()
def log_demo():
    """Emit representative log messages for CLI/flight-recorder tests.

    Emits DEBUG/INFO/WARNING/ERROR/CRITICAL messages on the 'calista.demo'
    logger and additional messages on a 'some.thirdparty' logger to exercise
    logger-level filtering and flight-recorder behavior.
    """
    logger = logging.getLogger("calista.demo")
    logger.debug("This is a debug-level test message.")
    logger.info("This is an info-level test message.")
    logger.warning("This is a warning-level test message.")
    logger.error("This is an error-level test message.")
    logger.critical("This is a critical-level test message.")
    third_party_logger = logging.getLogger("some.thirdparty")
    third_party_logger.debug("This is a debug-level third-party test message.")
    third_party_logger.info("This is an info-level third-party test message.")
    third_party_logger.warning("This is a warning-level third-party test message.")
    logger.debug("This is a final debug-level test message.")


def _remove_command_everywhere(group, name: str) -> None:
    """Remove a command from a Click group and its internal sections.

    Ensures the test-only command is removed from the group and any internal
    registries Click may use so cleanup is robust across Click versions.
    """
    group.commands.pop(name, None)
    if hasattr(group, "_default_section"):
        group._default_section.commands.pop(name, None)  # pylint: disable=protected-access
    for sec in getattr(group, "_sections", []):
        getattr(sec, "commands", {}).pop(name, None)


@pytest.fixture
def registered_log_demo():
    """Register the 'log-demo' command for the duration of a test.

    Adds the command to the top-level `calista` group before the test and
    removes it afterwards to avoid leaking test commands between tests.
    """
    calista.add_command(log_demo, name="log-demo")
    try:
        yield
    finally:
        _remove_command_everywhere(calista, "log-demo")


# 2) Fixture for a runner
@pytest.fixture
def runner():
    """Return a Click CliRunner for invoking CLI commands in tests."""
    return CliRunner()


# 3) Fixture for an isolated filesystem per test
@pytest.fixture
def fs(runner):
    """Provide an isolated filesystem context for tests using CliRunner.

    Uses runner.isolated_filesystem() to ensure filesystem side-effects are
    confined to the test.
    """
    with runner.isolated_filesystem():
        yield
