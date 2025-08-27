# ADR-0011: File Store Integration

**Status**: Accepted <br>
**Related**: ADR-0005 Event Store Schema, ADR-0006 Event Envelope

## Context

Large artifacts (FITS, calibrated images) must not bloat event store.

## Decision

- Store digest references (sha256) in events.
- Actual files live in CALISTA’s content-addressable file store.

## Consequences

- Event store remains lean.
- Provenance preserved by digest integrity.
