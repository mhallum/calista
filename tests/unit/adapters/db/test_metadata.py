"""Tests for SQLAlchemy naming conventions applied via `metadata`.

These tests verify that the configured naming_convention in
`calista.infrastructure.db.metadata` generates predictable, stable names
for indexes, unique constraints, and check constraints.

Why it matters:
    Alembic autogenerate relies on these deterministic names to avoid
    spurious diffs (e.g. repeatedly dropping and recreating constraints
    due to name mismatches). Locking the convention with tests ensures
    clean, stable migration history.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Column,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    inspect,
)

from calista.adapters.db.metadata import metadata

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


def test_index_naming_convention_for_single_and_multi_cols(
    sqlite_engine_memory: Engine,
):
    """Unnamed indexes should be auto-named by the SQLAlchemy naming_convention.

    This ensures Alembic autogenerate produces stable, deterministic
    index names, preventing spurious migration diffs.
    """
    engine = sqlite_engine_memory

    t = Table(  # noqa: F841 # pylint: disable=unused-variable # pyright: ignore[reportUnusedVariable]
        "t_meta_ix",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("a", String, nullable=False),
        Column("b", Integer),
        # Unnamed index → should be named by convention
        Index(None, "a"),
        Index(None, "a", "b"),
    )

    metadata.create_all(engine)

    db_index_inspector = inspect(engine)
    indexes = db_index_inspector.get_indexes("t_meta_ix")
    names = {ix["name"] for ix in indexes}

    # Expect convention-based names
    assert "ix_t_meta_ix_t_meta_ix_a" in names  # pylint: disable=magic-value-comparison
    assert "ix_t_meta_ix_t_meta_ix_a_t_meta_ix_b" in names  # pylint: disable=magic-value-comparison


def test_unique_constraint_uses_convention_name_or_unique_index_name(
    sqlite_engine_memory: Engine,
):
    """Unique constraints should be named by convention.

    Alembic relies on deterministic names to avoid repeatedly dropping and
    recreating constraints during autogenerate. On SQLite, UNIQUE constraints
    reflect as unique indexes, so we accept either form.
    """
    engine = sqlite_engine_memory

    t = Table(  # noqa: F841 # pylint: disable=unused-variable # pyright: ignore[reportUnusedVariable]
        "t_meta_uq",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("a", String, nullable=False),
        # Unnamed → convention should generate "uq_t_meta_uq_a"
        UniqueConstraint("a"),
    )
    metadata.create_all(engine)

    database_inspector = inspect(engine)
    # On SQLite, UNIQUE constraints are materialized as indexes.
    idx = {ix["name"]: ix for ix in database_inspector.get_indexes("t_meta_uq")}
    uq_names = {
        uc.get("name") for uc in database_inspector.get_unique_constraints("t_meta_uq")
    }

    # Accept either form depending on dialect/reflection:
    # pylint: disable=magic-value-comparison
    assert "uq_t_meta_uq_a" in idx or "uq_t_meta_uq_a" in uq_names


def test_check_constraint_uses_convention_with_explicit_name(
    sqlite_engine_memory: Engine,
):
    """Check constraints with explicit names should be prefixed by convention.

    This guarantees Alembic will generate stable check constraint names
    across migrations.
    """
    engine = sqlite_engine_memory

    t = Table(  # noqa: F841 # pylint: disable=unused-variable # pyright: ignore[reportUnusedVariable]
        "t_meta_ck",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("a", Integer),
        # Provide name=...; convention prefixes it with ck_<table>_
        CheckConstraint("a >= 0", name="nonneg"),
    )
    metadata.create_all(engine)

    inspector = inspect(engine)
    checks = inspector.get_check_constraints("t_meta_ck")
    names = {c.get("name") for c in checks if c.get("name")}
    # pylint: disable=magic-value-comparison
    assert "ck_t_meta_ck_nonneg" in names
