# Event Store Schema Overview

**Purpose**: Append-only log of domain events. No ad-hoc querying; projections handle reads.

**Columns**

- `global_seq`: Monotonic PK (BIGINT; PG identity)
- `event_id`: ULID (26 chars), unique
- `stream_id`, `stream_type`: stream identity
- `version`: optimistic concurrency per stream
- `payload`: event body (JSON/JSONB)
- `metadata`: transport/trace info (JSON/JSONB)
- `recorded_at`: UTC timestamp (server default)

**Constraints enforced here**

- ULID length == 26
- UNIQUE(stream_id, version)
- UNIQUE(event_id)
- version >= 1

See ADR-0005 for rationale and tradeoffs.
