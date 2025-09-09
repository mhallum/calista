"""Alembic round-trip smoke test for SQLite.

This test exercises the full *upgrade → downgrade* path against a temporary,
file-backed SQLite database to ensure:
  - `upgrade head` creates the `event_store` table, and
  - `downgrade base` drops it (and associated objects).

We use a file (not :memory:) so Alembic's schema changes persist across
connections within the test.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

from alembic import command
from calista import config

# mypy: disable-error-code=no-untyped-def


def test_alembic_downgrade_upgrade_roundtrip_sqlite_tmp(tmp_path: Path):
    """Upgrade to head (assert table exists) → downgrade to base (assert dropped).

    Uses `sqlite_master` to introspect table presence, which is stable on SQLite.
    """

    url = f"sqlite:///{tmp_path / 'calista.db'}"
    command.upgrade(config.build_alembic_config(url), "head")
    eng = create_engine(url, future=True)

    with eng.begin() as c:
        exists = c.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='event_store'"
            )
        ).fetchone()
        assert exists, "event_store should exist after upgrade"

    command.downgrade(config.build_alembic_config(url), "base")

    with eng.begin() as c:
        exists = c.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='event_store'"
            )
        ).fetchone()
        assert not exists, "event_store should be dropped after downgrade"

    eng.dispose()
