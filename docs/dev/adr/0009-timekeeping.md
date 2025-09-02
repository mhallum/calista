# ADR-0009: Timekeeping

**Status**: Accepted <br>
**Related**: ADR-0006 Event Envelope

## Context

Events must have reliable timestamps.

## Decision

- Store `recorded_at` as a timezone-aware UTC timestamp (`TIMESTAMPTZ` on Postgres). **When serialized** (logs, JSON, APIs), emit **RFC 3339 with** `Z`.

## Consequences

- Consistent ordering across environments.
- No timezone drift issues.
