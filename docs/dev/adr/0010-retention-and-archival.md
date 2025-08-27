# ADR-0010: Retention & Archival

**Status**: Accepted <br>
**Related**: ADR-0005 Event Store Schema

## Context

Event stores can grow unbounded with scientific data.

## Decision

- Events are append-only; never modified or deleted.
- Support snapshotting and archival exports for long-term storage.

## Consequences

- Preserves full provenance.
- Requires storage/archival strategy as datasets scale.
