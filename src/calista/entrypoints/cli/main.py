"""Calista CLI entry point.

Defines the top-level ``calista`` command (via Click-Extra) and registers
subcommands exposed by the project.

Currently available groups
- ``calista db`` — forward-only database management (upgrade/current/heads/history).

Notes
- The CLI version is sourced from `calista.__version__` and displayed
  automatically by Click-Extra (``--version``).
- Additional command groups should be registered here via ``calista.add_command(...)``.

Examples
    $ calista --version
    $ calista db upgrade
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import click
import click_extra as clickx
from platformdirs import user_log_dir

from calista import __version__
from calista.logging import config_console_handler, config_flight_recorder, log_startup

from .db import db as db_group
from .helpers import hyperlink
from .helpers.log_level_parser import parse_log_level

if TYPE_CHECKING:
    from logging import Handler

# pylint: disable=

logger = logging.getLogger(__name__)


HELP = """CALISTA command-line interface.

    CALISTA is a reproducible data-processing pipeline for astronomical data—covering
    photometry and spectroscopy. It turns raw observations into calibrated, measured
    results through deterministic steps, recording inputs, parameters, and versions so
    every outcome can be audited and regenerated.
    """


EPILOG = "\b\n" + "\n".join(
    [
        f"{click.style('See Also:', fg='blue', bold=True, underline=True)}",
        "  Docs  : " + hyperlink("https://mhallum.github.io/calista/"),
        "  Issues: " + hyperlink("https://github.com/mhallum/calista/issues"),
    ]
)


@clickx.extra_group(
    version=__version__,
    help=HELP,
    params=[
        clickx.ColorOption(show_envvar=True),
        clickx.TimerOption(show_envvar=True),
        clickx.ExtraVersionOption(),
    ],
    epilog=EPILOG,
)
@click.option(
    "--verbose",
    "-v",
    "verbose_count",
    count=True,
    help=(
        "Increase the default WARNING verbosity by one level"
        "for each additional repetition of the option."
    ),
    default=0,
)
@click.option(
    "--quiet",
    "-q",
    "quiet_count",
    count=True,
    help=(
        "Decrease the default WARNING verbosity by one level"
        "for each additional repetition of the option."
    ),
    default=0,
)
@click.option(
    "--debug/--no-debug",
    is_flag=True,
    help="Enable debug mode (enables extra developer diagnostics beyond -vvv).",
    default=False,
)
@click.option(
    "--log-path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to log file (overrides default flight recorder path).",
    default=Path(user_log_dir("calista", appauthor=False, ensure_exists=True))
    / "latest.log",
    envvar="CALISTA_LOG_PATH",
    show_default=True,
    show_envvar=True,
)
@click.option(
    "--flight-recorder-capacity",
    type=int,
    default=2000,
    hidden=True,
    envvar="CALISTA_FLIGHT_RECORDER_CAPACITY",
    show_envvar=True,
    help="Capacity of the flight recorder (in number of log records).",
)
@click.option(
    "--flight-recorder/--no-flight-recorder",
    "flight_recorder",
    is_flag=True,
    help=(
        "Enable the in-memory flight recorder. Keeps the last N log records "
        "(tunable via CALISTA_FLIGHT_RECORDER_CAPACITY) at DEBUG granularity (unaffected by -v/-q) "
        "and writes them to --log-path when a WARNING/ERROR occurs, or on clean exit "
        "if --force-flush is set. Console verbosity is unchanged. "
        "Use --no-flight-recorder to disable."
    ),
    default=True,
    show_envvar=True,
)
@click.option(
    "--force-flush/--no-force-flush",
    "force_flush_flight_recorder",
    is_flag=True,
    help=(
        "Force-flush the flight recorder buffer to --log-path on program exit. "
        "Normally the buffer only dumps on WARNING/ERROR; console output is unaffected. "
        "Env var CALISTA_FORCE_FLUSH_FLIGHT_RECORDER is treated as enabled if set "
        "(any non-empty value), disabled if unset. "
        "Use --no-force-flush to disable."
    ),
    default=False,
    show_default=True,
    show_envvar=True,
)
@click.option(
    "-L",
    "--logger-level",
    "logger_levels",
    multiple=True,  # repeatable option
    callback=parse_log_level,
    help=(
        "Set MINIMUM LEVEL for specific LOGGERS (NAME=LEVEL). This changes the "
        "logger's own level, so it applies to BOTH console and flight-recorder. "
        "Use to quiet verbose third-party libs. Repeatable (e.g. -L sqlalchemy=INFO "
        "-L alembic=WARNING) or via CALISTA_LOGGER_LEVELS (comma/space list)."
    ),
    default=("sqlalchemy=WARNING", "alembic=WARNING"),
    show_default=True,
    show_envvar=True,
)
@click.option(
    "--redactor-mode",
    "redactor_mode",
    type=click.Choice(["lenient", "strict"], case_sensitive=False),
    help=(
        "Set the redaction mode for logs and error messages. "
        "'lenient' (default) redact passwords/tokens but keep usernames/ids visible; "
        "'strict' redact passwords/tokens and also usernames/ids."
    ),
    default="lenient",
    show_envvar=True,
    show_default=True,
)
@clickx.pass_context
def calista(  # pylint: disable=too-many-arguments, too-many-locals, too-many-positional-arguments
    ctx: click.Context,
    verbose_count: int,
    quiet_count: int,
    debug: bool,
    log_path: Path,
    flight_recorder_capacity: int,
    flight_recorder: bool,
    force_flush_flight_recorder: bool,
    logger_levels: dict[str, int],
    redactor_mode: str,
) -> None:
    """CALISTA command-line interface."""

    # 0) compute effective verbosity
    base_level = logging.WARNING
    level = base_level - (10 * verbose_count) + (10 * quiet_count)
    level = max(logging.DEBUG, min(logging.CRITICAL, level))

    handlers: list[Handler] = []

    # 1) configure console handler
    use_color = ctx.color is not False  # None or True => allow color
    rich_handler = config_console_handler(
        level=level, debug_mode=debug, color=use_color
    )
    handlers.append(rich_handler)

    # 2) configure flight recorder
    if flight_recorder:
        flight_recorder_handler = config_flight_recorder(
            path=log_path,
            capacity=flight_recorder_capacity,
            flush_on_close=force_flush_flight_recorder,
        )
        handlers.append(flight_recorder_handler)

    # 3) Configure root logger with configured handlers
    logging.basicConfig(
        level=logging.DEBUG,  # capture all levels; handlers filter
        handlers=handlers,
        force=True,  # override any existing logging config
    )

    # 4) Set 3rd-party logger levels
    for name, lvl in logger_levels.items():
        logging.getLogger(name).setLevel(lvl)

    # 5) Log startup info
    log_startup(
        logger,
        app_version=__version__,
        level=level,
        handlers=handlers,
        log_path=log_path,
        flight_recorder=flight_recorder,
        flight_capacity=flight_recorder_capacity if flight_recorder else None,
        force_flush_fr=force_flush_flight_recorder,
        logger_levels=logger_levels,
        redactor_mode=redactor_mode,
    )

    # 6) Ensure logging is cleanly shutdown on program exit
    ctx.call_on_close(logging.shutdown)  # <- will run after the command returns


calista.add_command(db_group)
