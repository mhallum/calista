# ADR-0013: Querying & Projections

**Status**: Accepted <br>
**Related**: ADR-0005 Event Store, ADR-0006 Event Envelope, ADR-0012 Domain vs. Integration Events

## Context

The event store is optimized for writes and sequential reads (appends and replays). It should not be burdened with ad-hoc queries for reporting, analytics, or user interfaces.

In CALISTA, scientific workflows require queries such as:

- “List all BiasFrames ingested in session X.”
- “What are the latest calibrated ScienceFrames for target Y?”
- “Summarize nightly throughput statistics.”

Running these queries directly against the append-only event log would be inefficient and potentially compromise write performance.

## Decision

- The event store supports only:
  - Appends (storing new events).
  - Replay (reading streams or global sequences).
- All query use cases are served by read models / projections:
  - Projections are built by subscribing to event streams.
  - Read models are optimized for query patterns (e.g., Postgres tables, JSON indices, search indexes).
  - Multiple projections may exist for different consumers (e.g., photometry summaries, instrument usage reports).

## Consequences

- Establishes a clear CQRS boundary:
  - Command side = event store (append/replay).
  - Query side = projections / read models.
- Keeps the event store efficient and simple.
- Enables specialized query optimizations without polluting the core event log.
- Requires extra infrastructure (projection builders, read model refresh policies), but provides scalability and flexibility.
- Read models may become eventually consistent, which must be documented for users.
