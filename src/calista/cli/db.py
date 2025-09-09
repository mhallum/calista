"""Calista DB CLI — forward-only Alembic wrappers.

This module provides the `calista db` command group with a minimal, *forward-only*
interface over Alembic. It intentionally **does not** expose destructive operations
like `downgrade` or `stamp`, matching the event store's append-only posture.

Commands
- `current`  : Show the current DB revision.
- `heads`    : Show available head revisions.
- `history`  : Show migration history (supports `-v` and `-i`).
- `upgrade`  : Apply migrations up to a target revision (default: `head`).
               Prompts for confirmation unless `--force` is provided.
               Supports `--sql` to generate SQL without executing.

Requirements
- Environment variable **`CALISTA_DB_URL`** must be set (no resolver here).
  Example (bash):
      export CALISTA_DB_URL='postgresql+psycopg://USER:PASS@localhost:5432/calista'
  Example (PowerShell):
      $env:CALISTA_DB_URL='postgresql+psycopg://USER:PASS@localhost:5432/calista'
- Alembic configuration file **`alembic.ini`** is discovered by walking upward
  from this module's path; it should set:
      [alembic]
      script_location = src/calista/infrastructure/db/alembic


Examples
    $ calista db current
    $ calista db heads -v
    $ calista db history -vi
    $ calista db upgrade                     # upgrade to head, with confirmation
    $ calista db upgrade head --sql          # dry-run SQL
    $ calista db upgrade --force             # upgrade without confirmation

Failure Modes
- Missing `CALISTA_DB_URL` → ClickException with a setup hint.
- Missing `alembic.ini` → ClickException instructing to keep a root ini or
  configure programmatically.

Future Work (separate PRs)
- `calista db status` and `calista db doctor` for connectivity & invariant checks.
"""

import os
import sys

import click
import click_extra as clickx
from alembic import command

from calista import config

from .helpers import sanitize_url, success, warn

MISSING_DB_URL_MSG = (
    "CALISTA_DB_URL is not set.\n\n"
    "Set it before running this command, e.g.:\n"
    "  export CALISTA_DB_URL='postgresql+psycopg://USER:PASS@localhost:5432/calista'\n"
    "  # PowerShell:\n"
    "  $env:CALISTA_DB_URL='postgresql+psycopg://USER:PASS@localhost:5432/calista'"
)


@click.group(cls=clickx.ExtraGroup)
@click.pass_context
def db(ctx: click.Context) -> None:
    """Database management commands."""
    if not (url := os.environ.get("CALISTA_DB_URL")):
        raise click.ClickException(MISSING_DB_URL_MSG)

    cfg = config.build_alembic_config(url, stdout=sys.stdout)

    ctx.obj = {"url": url, "cfg": cfg}


@db.command()
@click.option(
    "--verbose",
    "-v",
    "verbose",
    is_flag=True,
    help="Show alembic's more verbose output.",
)
@click.pass_context
def current(ctx: click.Context, verbose: bool) -> None:
    """Show current DB revision."""
    command.current(ctx.obj["cfg"], verbose=verbose)


@db.command()
@click.option(
    "--verbose",
    "-v",
    "verbose",
    is_flag=True,
    help="Show alembic's more verbose output.",
)
@click.pass_context
def heads(ctx: click.Context, verbose: bool) -> None:
    """Show available head revisions."""
    command.heads(ctx.obj["cfg"], verbose=verbose)


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
@click.pass_context
def history(ctx: click.Context, verbose: bool, indicate_current: bool) -> None:
    """Show revision history."""
    command.history(ctx.obj["cfg"], verbose=verbose, indicate_current=indicate_current)


@db.command()  # pyright: ignore[reportFunctionMemberAccess]
@click.option("--sql", is_flag=True, help="Generate SQL without executing.")
@click.option("--force", is_flag=True, help="Upgrade without confirmation.")
@click.pass_context
def upgrade(ctx: click.Context, sql: bool, force: bool) -> None:
    """Upgrade the database to the head revision."""
    if not force and not sql:
        warn("This will upgrade the database at:")
        click.secho(f"  {click.style(sanitize_url(ctx.obj['url']), underline=True)}")
        click.confirm(
            click.style("  Are you sure you want to proceed?", fg="yellow"),
            abort=True,
        )
    command.upgrade(ctx.obj["cfg"], revision="head", sql=sql)
    success("Upgrade complete!")
