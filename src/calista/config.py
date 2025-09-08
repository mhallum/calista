"""Configuration utilities for CALISTA.

This module centralizes small helpers and constants related to application configuration.
"""

import sys
from importlib.resources import files
from pathlib import Path
from typing import TextIO

from alembic.config import Config

ROOT = Path(__file__).resolve().parents[2]

ALEMBIC_URL_KEY = "sqlalchemy.url"  # pragma: no mutate
ALEMBIC_SCRIPT_LOCATION_KEY = "script_location"  # pragma: no mutate


def build_alembic_config(db_url: str, stdout: TextIO = sys.stdout) -> Config:
    """Build an Alembic `Config` object for CALISTA's migrations.

    Sets only Alembic "main" options:
    - `sqlalchemy.url` → the database URL you pass
    - `script_location` → CALISTA's packaged Alembic scripts

    Args:
        db_url: SQLAlchemy database URL (e.g., `sqlite:///:memory:` or
            `postgresql+psycopg://user:pass@host/dbname`).
        stdout: Text stream Alembic will write status lines to. Defaults to
            `sys.stdout`; override in tests to capture output.

    Returns:
        An `alembic.config.Config` pointing to CALISTA's migration scripts.
    """
    cfg = Config(stdout=stdout)
    cfg.set_main_option(ALEMBIC_URL_KEY, db_url)
    cfg.set_main_option(
        ALEMBIC_SCRIPT_LOCATION_KEY,
        str(files("calista.infrastructure.db.alembic")),
    )
    return cfg
