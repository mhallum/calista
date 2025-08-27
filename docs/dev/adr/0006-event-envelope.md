# ADR-0006: Event Envelope

**Status**: Accepted <br>
**Related**: ADR-0005 Event Store

## Context

Events must share a consistent persisted structure.

## Decision

Canonical envelope fields:

- `global_seq`: Monotonic sequence number across all events.
- `stream_id`: Aggregate identifier (e.g., session ID, frame ID).
- `stream_type`: Aggregate type (e.g., Session, BiasFrame).
- `version`: Aggregate-local version number, incremented per event.
- `event_id`: Globally unique identifier (ULID).
- `recorded_at`: Timestamp when event was persisted (UTC, RFC3339).
- `payload` : Event data (domain-specific fields).
- `metadata`: System metadata (user, process ID, correlation ID, etc.).

## Consequences

- Ensures reliable replay of system history.
- Enables optimistic concurrency checks via `version`.
- Provides clear ordering across streams via `global_seq`.
- Separates domain concerns (`payload`) from system concerns (`metadata`).
- Extensible: new metadata fields can be added without breaking existing events.
