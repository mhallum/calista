# ADR-0007: Identifiers (UUID vs ULID)

**Status**: Accepted <br>
**Related**: ADR-0006 Event Envelope

## Context

Identifiers must provide **global uniqueness** (for deduplication and references) and **useful ordering** (for human/debug sorting). Different use cases apply to **event IDs** (single events) and **stream IDs** (aggregate streams).

## Decision

- **Event IDs** (`event_id`): Use **ULID** (128-bit; Crockford Base32, 26 chars).
  - Generate **monotonic ULIDs** to avoid collisions within the same millisecond.
  - ULID is sortable by _creation time_, but `global_seq` remains the source of truth for ordering.
- **Stream IDs** (`stream_id`): Use **domain-scoped identifiers**:
  - Prefer a **stable ULID per aggregate instance** (simple, uniform), **or** a natural key when it is globally unique and immutable (e.g., `Session:2024-10-05_LDT_01`).
  - Do **not** encode type inside the ID; type lives in `stream_type`.

## Consequences

- **Human-friendly** sorting of `event_id`aids debugging and log correlation.
- **Deterministic, unique IDs** support idempotency and cross-system references.
- Clear separation of concerns: **identity via ULID**, **ordering via** `global_seq`.
