"""Create event_store table

Revision ID: be411457bc58
Revises:
Create Date: 2025-09-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from calista.infrastructure.db.sa_types import BIGINT_PK, PORTABLE_JSON, UTCDateTime

# deal with alembic stuff
# pylint: disable=no-member

# revision identifiers, used by Alembic.
revision: str = "be411457bc58"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.create_table(
        "event_store",
        sa.Column(
            "global_seq",
            BIGINT_PK,
            sa.Identity(always=False, start=1),
            nullable=False,
            comment="Global, monotonically increasing sequence across all streams.",
        ),
        sa.Column(
            "stream_id",
            sa.String(length=200),
            nullable=False,
            comment="Logical stream identifier (e.g., aggregate ID).",
        ),
        sa.Column(
            "stream_type",
            sa.String(length=100),
            nullable=False,
            comment="Stream category/type (e.g., aggregate class).",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            comment="Per-stream version (starts at 1); used for optimistic concurrency.",
        ),
        sa.Column(
            "event_id",
            sa.String(length=26),
            nullable=False,
            comment="ULID (26 chars). Uniquely identifies this event.",
        ),
        sa.Column(
            "event_type",
            sa.String(length=120),
            nullable=False,
            comment="Fully-qualified event name used by projections/handlers.",
        ),
        sa.Column(
            "recorded_at",
            UTCDateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Server-assigned UTC timestamp (stored as TIMESTAMPTZ on Postgres).",
        ),
        sa.Column(
            "payload",
            PORTABLE_JSON,
            nullable=False,
            comment="Domain event payload (JSON object).",
        ),
        sa.Column(
            "metadata",
            PORTABLE_JSON,
            nullable=True,
            comment="Transport/headers (e.g., correlation_id, causation_id, actor).",
        ),
        sa.CheckConstraint(
            "length(event_id) = 26", name=op.f("ck_event_store_event_id_26_char")
        ),
        sa.CheckConstraint(
            "version >= 1", name=op.f("ck_event_store_positive_version")
        ),
        sa.PrimaryKeyConstraint("global_seq", name=op.f("pk_event_store")),
        sa.UniqueConstraint("event_id", name=op.f("uq_event_store_event_id")),
        sa.UniqueConstraint(
            "stream_id", "version", name=op.f("uq_event_store_stream_id_version")
        ),
        comment="Append-only event log. One row per domain event.",
    )
    op.create_index(
        op.f("ix_event_store_event_store_event_type"),
        "event_store",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_event_store_event_store_stream_id_event_store_global_seq"),
        "event_store",
        ["stream_id", "global_seq"],
        unique=False,
    )
    op.create_index(
        op.f("ix_event_store_event_store_stream_type_event_store_event_type"),
        "event_store",
        ["stream_type", "event_type"],
        unique=False,
    )

    # Postgres specific
    if dialect == "postgresql":  # pylint: disable=magic-value-comparison
        # PG-only JSONB GIN indexes (nice-to-have for projections/filters)
        op.create_index(
            "ix_event_store_payload_gin",
            "event_store",
            ["payload"],
            postgresql_using="gin",
        )
        op.create_index(
            "ix_event_store_metadata_gin",
            "event_store",
            ["metadata"],
            postgresql_using="gin",
        )

    # ---- APPEND-ONLY ENFORCEMENT ----
    if dialect == "postgresql":  # pylint: disable=magic-value-comparison
        # One trigger function handles both UPDATE and DELETE by raising
        op.execute(
            """
            CREATE OR REPLACE FUNCTION event_store_forbid_mod() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
              RAISE EXCEPTION 'event_store is append-only; % not allowed', TG_OP
              USING ERRCODE = '0A000'; -- feature_not_supported
            END;
            $$;
            """
        )
        op.execute(
            """
            CREATE TRIGGER tr_event_store_append_only
            BEFORE UPDATE OR DELETE ON event_store
            FOR EACH ROW
            EXECUTE FUNCTION event_store_forbid_mod();
            """
        )
    else:
        # SQLite: separate BEFORE triggers with RAISE(ABORT, ...)
        op.execute(
            """
            CREATE TRIGGER tr_event_store_no_update
            BEFORE UPDATE ON event_store
            BEGIN
              SELECT RAISE(ABORT, 'event_store is append-only; UPDATE not allowed');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER tr_event_store_no_delete
            BEFORE DELETE ON event_store
            BEGIN
              SELECT RAISE(ABORT, 'event_store is append-only; DELETE not allowed');
            END;
            """
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Drop append-only triggers first
    if dialect == "postgresql":  # pylint: disable=magic-value-comparison,R6103
        op.execute("DROP TRIGGER IF EXISTS tr_event_store_append_only ON event_store;")
        op.execute("DROP FUNCTION IF EXISTS event_store_forbid_mod();")
    else:
        op.execute("DROP TRIGGER IF EXISTS tr_event_store_no_delete;")
        op.execute("DROP TRIGGER IF EXISTS tr_event_store_no_update;")

    # Drop the rest

    op.drop_index(
        op.f("ix_event_store_event_store_stream_type_event_store_event_type"),
        table_name="event_store",
    )
    op.drop_index(
        op.f("ix_event_store_event_store_stream_id_event_store_global_seq"),
        table_name="event_store",
    )
    op.drop_index(
        op.f("ix_event_store_event_store_event_type"), table_name="event_store"
    )

    if dialect == "postgresql":  # pylint: disable=magic-value-comparison
        op.drop_index("ix_event_store_metadata_gin", table_name="event_store")
        op.drop_index("ix_event_store_payload_gin", table_name="event_store")

    op.drop_table("event_store")
