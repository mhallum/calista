"""Alembic round-trip smoke test for PostgreSQL.

This test validates that our migrations can *upgrade to head* and *downgrade to base*
cleanly on a real PostgreSQL 17 instance. It uses Testcontainers to provision a
temporary server, creates a scratch database via an AUTOCOMMIT admin connection,
then:

  1) runs `alembic upgrade head`,
  2) asserts `event_store` exists and accepts a typed insert (JSON/JSONB adapts),
  3) runs `alembic downgrade base`,
  4) asserts `event_store` is dropped.

We operate on a per-test scratch DB so the container’s default DB remains intact.
"""

import re
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, insert, text
from testcontainers.postgres import (  # pyright: ignore[reportMissingTypeStubs]
    PostgresContainer,
)

from alembic import command
from alembic.config import Config
from calista.adapters.eventstore.schema import event_store  # <-- use your Table

# mypy: disable-error-code=no-untyped-def


def _cfg(url: str) -> Config:
    """Build an Alembic Config pointed at this repo’s `alembic.ini`, overriding the URL.

    Args:
        url: Full SQLAlchemy database URL that Alembic should target.

    Returns:
        Config: An Alembic configuration object with `sqlalchemy.url` set.
    """
    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_alembic_downgrade_upgrade_roundtrip_postgres(
    make_event: Callable[..., dict[str, Any]],
):
    """Upgrade → assert → Downgrade → assert on a scratch Postgres database.

    Steps:
      * Start Postgres 17 (Testcontainers).
      * Create a scratch DB via AUTOCOMMIT on the `postgres` admin DB.
      * `alembic upgrade head`, assert `event_store` exists, perform a typed insert.
      * `alembic downgrade base`, assert `event_store` no longer exists.
      * Drop the scratch DB.
    """
    with PostgresContainer(
        "postgres:17", username="calista", password="changeme", dbname="calista"
    ) as pg:
        base_url = re.sub(r"\+psycopg2(?=:|$|/)", "+psycopg", pg.get_connection_url())

        # Use the 'postgres' DB for admin ops (not the DB we’ll drop)
        admin_url = re.sub(r"/[^/]+$", "/postgres", base_url)
        scratch = f"calista_rt_{uuid.uuid4().hex[:8]}"

        admin = create_engine(admin_url, future=True, pool_pre_ping=True)

        # AUTOCOMMIT for CREATE/DROP DATABASE
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :d AND pid <> pg_backend_pid()"
                ),
                {"d": scratch},
            )
            conn.execute(text(f"DROP DATABASE IF EXISTS {scratch}"))
            conn.execute(text(f"CREATE DATABASE {scratch}"))

        # now use the scratch DB
        url = re.sub(r"/[^/]+$", f"/{scratch}", base_url)

        # upgrade -> assert -> downgrade -> assert
        command.upgrade(_cfg(url), "head")
        eng = create_engine(url, future=True, pool_pre_ping=True)
        with eng.begin() as c:
            exists = c.execute(
                text("""
                SELECT EXISTS (
                  SELECT 1 FROM information_schema.tables
                  WHERE table_schema='public' AND table_name='event_store'
                )
            """)
            ).scalar()
            assert exists

            # Use typed insert so JSON/JSONB adapts correctly
            c.execute(insert(event_store).values(make_event()))

        command.downgrade(_cfg(url), "base")
        with eng.begin() as c:
            exists = c.execute(
                text("SELECT to_regclass('public.event_store') IS NOT NULL")
            ).scalar()
            assert not exists

        eng.dispose()

        # clean up the scratch DB (autocommit again)
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :d AND pid <> pg_backend_pid()"
                ),
                {"d": scratch},
            )
            conn.execute(text(f"DROP DATABASE IF EXISTS {scratch}"))
        admin.dispose()
