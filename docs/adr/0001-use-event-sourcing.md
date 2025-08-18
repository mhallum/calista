# ADR 0001: Use Event Sourcing

**Status**: Accepted

## Context

We need reproducibility and audit trails for scientific results.

## Decision

Represent domain state as an append-only stream of domain events.

## Consequences:

- ✅ Enables replay, reproducibility, and debugging.
- ✅ Easy to build multiple projections (e.g., light curves, QC reports).
- ❌ Adds complexity; projections must be managed.
