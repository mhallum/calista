# ADR-0005: Event Store

**Status**: Accepted <br>
**Related**: ADR-0003 Database, ADR-0004 Schema Migrations

## Context

CALISTA requires an append-only event log accross aggregates.

## Decision

- **Storage**: Relational table `event_store`.
- **Backends**: Postgres for runtime, SQLite for dev/CI.
- **Format**: Payload/metdata as JSON (Postgres JSONB, SQLite TEXT).

## Consequences

- Leverages RDBMS ACID guarantees.
- Simple and portable.
- Must handle JSON differences across dialects
