# ADR-0012: Domain vs Integration Events

**Status**: Accepted <br>
**Related**: ADR-0005 Event Store, ADR-0006 Event Envelope

## Context

Not all events have the same audience:

- **Domain events** represent internal state changes in CALISTA’s aggregates (e.g., `BiasFrameRegistered`, `LightFrameCalibrated`).
  - They are persisted in the event store for provenance, replay, and aggregate reconstruction.
  - Consumers: CALISTA’s own projections, policies, workflows.
- Integration events are derived from domain events but are intended for external systems (e.g., notifications, downstream pipelines, message bus).
  - They often have a more stable, public contract and may exclude sensitive internal details.
  - Consumers: other services, external APIs, monitoring, or user-facing tooling.

If CALISTA persisted integration events directly, it would leak internal implementation details and tightly couple the system to external consumers.

## Decision

- **Domain events**: Persist all aggregate domain events in the event store. They are the single source of truth for system state.
- **Integration events**: Derive and publish as needed:
  Through a **message bus** (for async processing).
  Through an **outbox table** pattern (for reliable delivery).
  May use transformed/enriched representations of domain events.

## Consequences

- Ensures internal consistency: all state changes are tracked in the event store.
- Prevents leaking sensitive or unstable internal details to external consumers.
- Allows clear contracts for external integrations while CALISTA’s domain model can evolve freely.
- Introduces an additional translation step (domain → integration), but this separation improves long-term maintainability.
