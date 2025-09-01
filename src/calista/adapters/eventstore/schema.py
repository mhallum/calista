"""Event store schema.

Defines the append-only ``event_store`` table used by CALISTA to persist domain
events. Each row is a single event with a globally ordered sequence, per-stream
version, and UTC timestamp.

Related ADRs (Non-exhaustive):

  - ADR-0003: Database
  - ADR-0004: Schema Migrations
  - ADR-0005: Event Store
  - ADR-0006: Event Envelope
  - ADR-0012: Domain vs Integration Events
  - ADR-0013: Querying & Projections
  - ADR-0014: Event Store Testing Strategy


Constraints (enforced here):

| Constraint                     | Purpose                         |
|--------------------------------|---------------------------------|
| UNIQUE(stream_id, version)     | per-stream optimistic concurrency |
| UNIQUE(event_id)               | ULID uniqueness                  |
| CHECK(char_length(event_id)=26)| ULID length                      |
| CHECK(version >= 1)            | versioning starts at 1           |


Append-only enforcement is applied in migrations (see ADR-0004).
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    Identity,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    text,
)

from calista.infrastructure.db.metadata import metadata
from calista.infrastructure.db.sa_types import BIGINT_PK, PORTABLE_JSON, UTCDateTime

__all__ = ["event_store"]

event_store = Table(
    "event_store",
    metadata,
    # Portable auto-increment primary key:
    # - Postgres: BIGINT IDENTITY
    # - SQLite: rowid-backed autoincrement (primary_key=True is sufficient)
    Column(
        "global_seq",
        BIGINT_PK,
        Identity(start=1),
        nullable=False,
        primary_key=True,
        comment="Global, monotonically increasing sequence across all streams.",
    ),
    Column(
        "stream_id",
        String(200),
        nullable=False,
        comment="Logical stream identifier (e.g., aggregate ID).",
    ),
    Column(
        "stream_type",
        String(100),
        nullable=False,
        comment="Stream category/type (e.g., aggregate class).",
    ),
    Column(
        "version",
        Integer,
        nullable=False,
        comment="Per-stream version (starts at 1); used for optimistic concurrency.",
    ),
    Column(
        "event_id",
        String(26),
        nullable=False,
        unique=True,
        comment="ULID (26 chars). Uniquely identifies this event.",
    ),
    Column(
        "event_type",
        String(120),
        nullable=False,
        comment="Fully-qualified event name used by projections/handlers.",
    ),
    # Server-assigned timestamp (portable default):
    Column(
        "recorded_at",
        UTCDateTime(),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Server-assigned UTC timestamp (stored as TIMESTAMPTZ on Postgres).",
    ),
    Column(
        "payload",
        PORTABLE_JSON,
        nullable=False,
        comment="Domain event payload (JSON object).",
    ),
    Column(
        "metadata",
        PORTABLE_JSON,
        nullable=True,
        comment="Transport/headers (e.g., correlation_id, causation_id, actor).",
    ),
    UniqueConstraint("stream_id", "version"),
    CheckConstraint("version >= 1", name="positive_version"),
    CheckConstraint("length(event_id) = 26", name="event_id_26_char"),
    Index(None, "stream_type", "event_type"),
    Index(None, "stream_id", "global_seq"),
    Index(None, "event_type"),
    comment="Append-only event log. One row per domain event.",
)
