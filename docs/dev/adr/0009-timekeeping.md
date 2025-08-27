# ADR-0009: Timekeeping

**Status**: Accepted <br>
**Related**: ADR-0006 Event Envelope

## Context

Events must have reliable timestamps.

## Decision

- Store `recorded_at` in UTC, RFC3339 format.

## Consequences

- Consistent ordering across environments.
- No timezone drift issues.
