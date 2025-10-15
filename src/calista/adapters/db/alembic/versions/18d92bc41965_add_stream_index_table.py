"""add stream_index table

Revision ID: 18d92bc41965
Revises: be411457bc58
Create Date: 2025-10-08 20:52:00.236973

"""

# pylint: disable=invalid-name

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# deal with alembic stuff
# pylint: disable=no-member

# revision identifiers, used by Alembic.
revision: str = "18d92bc41965"
down_revision: str | Sequence[str] | None = "be411457bc58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "stream_index",
        sa.Column(
            "kind",
            sa.String(length=64),
            nullable=False,
            comment="Stream kind/category.",
        ),
        sa.Column(
            "key",
            sa.String(length=512),
            nullable=False,
            comment="Natural key for the stream.",
        ),
        sa.Column(
            "stream_id",
            sa.String(length=26),
            nullable=False,
            comment="Unique stream identifier.",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            comment="Stream version.",
            server_default="0",
        ),
        sa.PrimaryKeyConstraint("kind", "key", name=op.f("pk_stream_index")),
        sa.UniqueConstraint("stream_id", name=op.f("uq_stream_index_stream_id")),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table("stream_index")
