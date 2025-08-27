# ADR-0008: Concurrency & Versioning

**Status**: Accepted <br>
**Related**: ADR-0006 Event Envelope

## Context

Multiple writers may append to same stream.

## Decision

- Use optimistic concurrency control via `version`.
- Insert fails if expected version mismatch.

## Consequences

- Prevents lost updates.
- Requires retry handling at caller.
