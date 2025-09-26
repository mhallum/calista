"""Logging helpers used by the Calista CLI and application.

This module provides utilities for configuring console logging with Rich
and an in-memory "flight recorder" that buffers log records and writes them
to disk on flush. It also provides a filter that annotates third-party
log records with a short prefix used by console formatting.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from logging.handlers import MemoryHandler
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeAlias

import alembic
import sqlalchemy
from rich.console import Console
from rich.logging import RichHandler

if TYPE_CHECKING:
    from logging import Logger

# pylint: disable=too-few-public-methods

PROJECT_PREFIX = "calista"


class ThirdPartyPrefixFilter(logging.Filter):
    """Annotate third-party log records with a short prefix.

    For records whose logger name does not start with the project prefix,
    sets `record.prefix` to a short bracketed token like "[urllib3]". For
    project loggers the prefix is set to an empty string. The filter always
    returns True to allow the record to be processed.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach a prefix to the record and allow it through.

        Args:
            record: The LogRecord being processed.

        Returns:
            bool: Always True (record is not filtered out).
        """
        if not record.name.startswith(PROJECT_PREFIX):
            # e.g. "urllib3.connectionpool" -> "[urllib3]"
            record.prefix = f"[{record.name.split('.')[0]}]"
        else:
            record.prefix = ""  # no prefix for calista logs
        return True


def config_console_handler(
    level: int = logging.INFO, debug_mode: bool = False, color: bool = True
) -> RichHandler:
    """Configure and return a RichHandler for console output.

    The handler writes to stderr and supports optional color and a debug
    mode. In debug mode the handler is set to DEBUG and includes source
    file/line information; otherwise a short third-party prefix is applied.

    Args:
        level: Minimum level for console output (overridden to DEBUG in debug_mode).
        debug_mode: When True, enable debug formatting (show_path, timestamps).
        color: Enable color output when True.

    Returns:
        RichHandler: Configured handler suitable to attach to the root logger.
    """

    # If color is False, disable color output
    # This is to keep it consistent with click-extra's --color / --no-color option
    ColorSystem: TypeAlias = Literal["auto", "standard", "256", "truecolor", "windows"]
    color_system: ColorSystem | None = "auto" if color else None

    # Create a console instance with the determined color system, and stderr=True
    console = Console(color_system=color_system, stderr=True)

    # change level if debug_mode is enabled
    if debug_mode:
        level = logging.DEBUG

    # Create Rich Handler with the specified level and console
    # In debug mode, show_path is enabled to show file paths in logs
    handler = RichHandler(
        level=level,
        console=console,
        rich_tracebacks=True,
        show_time=False,
        show_path=debug_mode,
        enable_link_path=debug_mode,
    )

    # determine and set formatter
    fmt = (
        "%(prefix)s %(message)s"
        if not debug_mode
        else "%(asctime)s %(name)s: %(message)s"
    )
    handler.setFormatter(logging.Formatter(fmt=fmt))

    # If not in debug mode, add a prefix to third-party logs
    if not debug_mode:
        handler.addFilter(ThirdPartyPrefixFilter())

    return handler


def config_flight_recorder(
    path: Path,
    capacity: int = 2000,
    flush_level: int = logging.WARNING,
    flush_on_close: bool = False,
) -> MemoryHandler:
    """Configure and return an in-memory flight recorder backed by a file.

    The flight recorder buffers up to `capacity` log records and flushes
    them to the provided file handler when a record at `flush_level` or
    higher is emitted (or on close if `flush_on_close` is True).

    Args:
        path: Destination file path for flushed records.
        capacity: Number of records to buffer in memory.
        flush_level: Level at or above which the buffer will be flushed.
        flush_on_close: If True, flush the buffer when the handler is closed.

    Returns:
        MemoryHandler: A memory-backed handler with a FileHandler target.
    """

    # Create a file handler for the flight recorder
    file_handler = logging.FileHandler(path, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] [%(process)d:%(threadName)s] %(levelname)s %(name)s:%(lineno)d: %(message)s"
        )
    )

    memory_handler = MemoryHandler(
        capacity=capacity,
        flushLevel=flush_level,
        target=file_handler,
        flushOnClose=flush_on_close,
    )

    return memory_handler


def log_startup(  # pylint: disable=too-many-arguments
    logger: Logger,
    *,
    app_version: str,
    level: int,
    handlers: list[logging.Handler],
    log_path: Path | None,
    flight_recorder: bool,
    flight_capacity: int | None,
    force_flush_fr: bool,
    logger_levels: dict[str, int],
) -> None:
    """Log human-friendly startup info and detailed diagnostics.

    Emits an informational one-line summary describing the application version
    and whether console logging and the flight-recorder are enabled. Additional
    DEBUG-level diagnostics are emitted for troubleshooting, including Python
    and platform versions, process id, current working directory, Alembic and
    SQLAlchemy versions, the active handler types, flight-recorder settings,
    and any per-logger overrides.

    Args:
        logger: Logger used to emit startup messages.
        app_version: Application version string to display.
        level: Effective console logging level (numeric).
        handlers: Active logging handlers attached to the root logger.
        log_path: Path to the flight-recorder output file, or None.
        flight_recorder: Whether the in-memory flight recorder is enabled.
        flight_capacity: Configured capacity of the flight recorder buffer, or None.
        force_flush_fr: Whether the flight recorder is configured to flush on close.
        logger_levels: Mapping of logger names to their configured numeric levels.
    """

    # Human-friendly one-liner
    logger.info(
        "CALISTA %s — console=%s, flight-recorder=%s",
        app_version,
        logging.getLevelName(level),
        "ON" if flight_recorder else "OFF",
    )

    # Deep diagnostics
    logger.debug("Python: %s", sys.version.split()[0])
    logger.debug("Platform: %s %s", platform.system(), platform.release())
    logger.debug("PID: %s", os.getpid())
    logger.debug("CWD: %s", Path.cwd())
    logger.debug("Alembic: %s", alembic.__version__)
    logger.debug("SQLAlchemy: %s", sqlalchemy.__version__)
    logger.debug(
        "Handlers: %s",
        [type(h).__name__ for h in handlers],
    )
    if flight_recorder:
        logger.debug(
            "Flight recorder: path=%s, capacity=%s, flush_on_close=%s",
            str(log_path) if log_path else "<none>",
            flight_capacity,
            force_flush_fr,
        )
    if logger_levels:
        logger.debug(
            "Per-logger overrides: %s",
            {name: logging.getLevelName(lvl) for name, lvl in logger_levels.items()},
        )
    else:
        # This should never happen because of defaults, but is here as a fallback.
        logger.debug("Per-logger overrides: <none>")  # pragma: no cover.
