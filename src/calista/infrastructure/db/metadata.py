"""Shared SQLAlchemy `MetaData` object with a naming convention.

This metadata is imported by all table definitions so that constraints
and indexes receive deterministic names. Deterministic naming is
critical for Alembic autogenerate: without it, migration scripts may
include spurious drops/adds due to randomly generated identifiers.

Naming convention:
    - Indexes:       ix_<table>_<col...>
    - Unique:        uq_<table>_<col...>
    - Check:         ck_<table>_<constraint_name>
    - Foreign keys:  fk_<table>_<col...>_<reftable>
    - Primary key:   pk_<table>
"""

from sqlalchemy import MetaData

#: Global metadata with enforced naming convention.
#: All CALISTA tables must attach to this metadata object.
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_label)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)
