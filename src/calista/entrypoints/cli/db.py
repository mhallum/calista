"""CALISTA DB CLI — forward-only Alembic wrappers.

Provides a minimal, forward-only interface over Alembic aligned with CALISTA's
append-only posture. Destructive operations (e.g., ``downgrade``, ``stamp``)
are intentionally omitted.

Behavior
- Uses programmatic Alembic configuration; human-oriented notices go to **stderr**,
  Alembic output to **stdout** to keep machine-readable flows intact.
- Schema-changing actions prompt for confirmation unless explicitly bypassed.

Requirements
- ``CALISTA_DB_URL`` must be set (no resolver here).
- Alembic config is discovered via ``config.build_alembic_config``; its
  ``[alembic] script_location`` should point to
  ``src/calista/infrastructure/db/alembic``.

Failure modes
- Missing/invalid ``CALISTA_DB_URL`` or unreachable DB → ``ClickException`` with guidance.
- Missing Alembic config → ``ClickException`` describing how to supply config.

Notes
- A future “doctor” command may add deeper health/invariant checks (separate PR).
"""

from __future__ import annotations

import sys
from enum import Enum
from typing import TYPE_CHECKING

import click
import click_extra as clickx
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import ArgumentError, OperationalError

from calista import config
from calista.adapters.db.engine import make_engine

from .helpers import error, sanitize_url, success, warn

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

MISSING_DB_URL_MSG = (
    "CALISTA_DB_URL is not set.\n\n"
    "Set it before running this command, e.g.:\n"
    "  export CALISTA_DB_URL='postgresql+psycopg://USER:PASS@localhost:5432/calista'\n"
    "  or in PowerShell:\n"
    "  $env:CALISTA_DB_URL='postgresql+psycopg://USER:PASS@localhost:5432/calista'"
)

INVALID_URL_FORMAT_MSG = (
    "The value of CALISTA_DB_URL is not a valid SQLAlchemy database URL."
)

CANNOT_CONNECT_MSG = (
    "CALISTA_DB_URL is set, but the database is not reachable.\n"
    "Please ensure the database is running and the URL is correct."
)

UPGRADE_SCHEMA_WARNING = (
    "This will upgrade the database schema to the latest version.\n"
    "Please ensure you have a backup before proceeding."
)

UPGRADE_SCHEMA_INSTRUCTIONS = "Run 'calista db upgrade' to update the schema."


def _check_connection(url: str) -> None:
    engine = make_engine(url)
    stmt = text("SELECT 1")  # pragma: no mutate
    with engine.connect() as conn:
        conn.execute(stmt)


def _get_url() -> str:
    try:
        url = config.get_db_url()
    except config.DatabaseUrlNotSetError as e:
        raise click.ClickException(MISSING_DB_URL_MSG) from e
    try:
        _check_connection(url)
    except OperationalError as e:
        raise click.ClickException(CANNOT_CONNECT_MSG) from e
    except ArgumentError as e:
        raise click.ClickException(INVALID_URL_FORMAT_MSG) from e
    return url


@click.group(cls=clickx.ExtraGroup)
def db() -> None:
    """Database management commands."""


@db.command()
@click.option(
    "--verbose",
    "-v",
    "verbose",
    is_flag=True,
    help="Show alembic's more verbose output.",
)
def current(verbose: bool) -> None:
    """Show current DB revision."""
    url = _get_url()
    cfg = config.build_alembic_config(db_url=url, stdout=sys.stdout)
    command.current(cfg, verbose=verbose)


@db.command()
@click.option(
    "--verbose",
    "-v",
    "verbose",
    is_flag=True,
    help="Show alembic's more verbose output.",
)
def heads(verbose: bool) -> None:
    """Show available head revisions."""
    cfg = config.build_alembic_config(stdout=sys.stdout)
    command.heads(cfg, verbose=verbose)


@db.command()  # pyright: ignore[reportFunctionMemberAccess]
@click.option(
    "--verbose",
    "-v",
    "verbose",
    is_flag=True,
    help="Show alembic's more verbose output.",
)
@click.option(
    "--indicate-current",
    "-i",
    "indicate_current",
    is_flag=True,
    help="Indicate the current revision.",
)
def history(verbose: bool, indicate_current: bool) -> None:
    """Show revision history."""
    cfg = (
        config.build_alembic_config(db_url=_get_url(), stdout=sys.stdout)
        if indicate_current
        else config.build_alembic_config(stdout=sys.stdout)
    )

    command.history(cfg, verbose=verbose, indicate_current=indicate_current)


@db.command()  # pyright: ignore[reportFunctionMemberAccess]
@click.option("--sql", is_flag=True, help="Generate SQL without executing.")
@click.option("--force", is_flag=True, help="Upgrade without confirmation.")
def upgrade(sql: bool, force: bool) -> None:
    """Upgrade the database to the head revision."""
    url = _get_url()
    cfg = config.build_alembic_config(db_url=url, stdout=sys.stdout)
    if not force and not sql:
        warn(UPGRADE_SCHEMA_WARNING)
        click.secho(f"db: {click.style(sanitize_url(url), underline=True)}")
        click.confirm(
            click.style("Are you sure you want to proceed?"),
            abort=True,
        )
    command.upgrade(cfg, revision="head", sql=sql)
    success("Upgrade complete!")


def _get_current_revision(engine: Engine) -> str | None:
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        return ctx.get_current_revision()


def _get_head_revision(cfg: Config) -> str | None:
    script = ScriptDirectory.from_config(cfg)
    if results := script.get_heads():
        return results[0]
    # Should not happen since we always have at least one head, but here as a fallback.
    return None  # pragma: nocover


class MigrationStatus(Enum):
    """Describes the migration status of the database schema."""

    UP_TO_DATE = "up to date"
    OUT_OF_DATE = "out of date"
    UNINITIALIZED = "uninitialized"


@db.command()
def status() -> None:
    """Show database connection and schema status."""
    try:
        engine = make_engine(_get_url())
    except Exception as e:  # pylint: disable=broad-except
        error("Cannot connect to database")
        click.echo(str(e))
    else:
        success("Database reachable")
        click.echo(f"Backend : {engine.dialect.name}")
        click.echo(f"URL     : {sanitize_url(str(engine.url))}")
        cfg = config.build_alembic_config(db_url=str(engine.url))
        rev = _get_current_revision(engine)
        head = _get_head_revision(cfg)
        if rev == head:
            migration_status = MigrationStatus.UP_TO_DATE
        elif rev is None:
            migration_status = MigrationStatus.UNINITIALIZED
        else:
            # This won't happen yet since we only have one revision, but here for future-proofing.
            migration_status = MigrationStatus.OUT_OF_DATE  # pragma: nocover

        message = (
            f"{rev} ({migration_status.value})"
            if rev is not None
            else f"{migration_status.value}"
        )
        click.echo(f"Schema  : {message}")

        if migration_status != MigrationStatus.UP_TO_DATE:
            warn("Run 'calista db upgrade' to update the schema.")
