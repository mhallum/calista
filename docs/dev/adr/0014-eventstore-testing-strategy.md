# ADR-0014: Event Store Testing Strategy

**Status**: Accepted <br>
**Related**: ADR-0005 Event Store, ADR-0004 Schema Migrations

## Context

The event store underpins all provenance in CALISTA.

- Bugs here could compromise reproducibility of scientific results.
- Tests must cover both **logical correctness** (append, replay, concurrency) and **infrastructure reliability** (migrations, dialect differences).
- CI/CD must validate behavior across Postgres (runtime) and SQLite (dev/CI).

## Decision

- **Unit Tests (fast):**

  - Run against in-memory or SQLite.
  - Cover core logic (append, replay, optimistic concurrency).
  - Validate envelope format and integrity rules.

- **Integration Tests (real backend):**

  - Run against Postgres in CI.
  - Exercise migrations, indexing, and dialect guards (JSONB vs TEXT).
  - Include concurrent writer scenarios and crash recovery.

- **Replay Fixtures:**

  - Define deterministic event streams as fixtures.
  - Re-run replays to confirm aggregates are reconstructed identically.
  - Validate idempotency and version checks.

- **Continuous Integration:**
  - Run both SQLite and Postgres tests in the matrix.
  - Enforce high coverage, including edge cases (duplicate event_id, stale version, out-of-order replay).

## Consequences

- Ensures **high confidence in correctness** across environments.
- Provides **deterministic replay validation**, crucial for provenance.
- Surfaces **dialect-specific differences** early (Postgres vs SQLite).
- Increases CI runtime slightly, but prevents regressions in the most critical subsystem.
