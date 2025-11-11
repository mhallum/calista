"""Alembic environment for CALISTA.

Policy defaults:
  - compare_type=True (catch column type drift)
  - compare_server_default=True (catch server default drift)
  - render_as_batch=True on SQLite (safe ALTER TABLE emulation)
  - URL precedence: `-x url=...` > config sqlalchemy.url > CALISTA_DB_URL
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure models/metadata are imported so autogenerate sees them
import calista.adapters.eventstore.sqlalchemy_adapters.schema  # noqa: F401 # pylint: disable=unused-import
from calista.adapters.db.metadata import metadata

# disable warning to deal with alembic context
# pylint: disable=no-member

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


# Resolve DB URL from env at runtime
def get_url() -> str:
    """Resolve DB URL with precedence: `-x url` > config > env."""

    # 1) `alembic -x url=...`
    xargs = context.get_x_argument(as_dictionary=True)
    url = xargs.get("url")

    # 2) alembic.ini / programmatic config
    if not url:
        url = config.get_main_option("sqlalchemy.url")

    # 3) environment variable
    if not url or "%(" in url:  # treat placeholder as unset # pylint: disable=R2004
        url = os.environ.get("CALISTA_DB_URL")

    if not url:
        raise RuntimeError("Set CALISTA_DB_URL to your database URL.")
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    url = get_url()
    connectable = engine_from_config(
        {"sqlalchemy.url": url},  # <— inject directly, ignore alembic.ini
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"  # pylint: disable=R2004
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=is_sqlite,  # needed for SQLite ALTER TABLE emulation
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
