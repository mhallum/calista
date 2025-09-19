# ADR-0021: Event Store Error Semantics & Read Behavior

**Status**: Accepted <br>
**Related**: ADR-0005 Event Store, ADR-0006 Event Envelope, ADR-0020 EventStore.append Return Semantics

## Context

Our event store must expose a clear, adapter-agnostic error model so service-layer code and tests behave consistently across SQLite/Postgres. We need to define:

- Which conditions are caller errors vs storage failures
- How batch appends behave (atomicity, single-stream policy)
- What reads return for empty results
- How DB constraint violations map to typed exceptions

## Decision

1) **Append is atomic & single-stream**
   - A single `append()` call must contain events for **one** `(stream_type, stream_id)`.
   - The write is **all-or-nothing** (transactional).

2) **Typed exceptions**
   - `VersionConflictError`: stream version precondition violated (e.g., `(stream_id, version)` already exists or non-contiguous versions in the batch).
   - `DuplicateEventIdError`: `event_id` not globally unique.
   - `InvalidEnvelopeError`: client-side validation failure before hitting DB (e.g., naive `recorded_at`, `version < 1`, mixed streams in the batch, non-serializable `payload/metadata`, field lengths).
   - `StoreUnavailableError`: connectivity/timeout/transaction aborts not attributable to caller preconditions.
   - All inherit from `EventStoreError`.

3) **Read behavior**
   - `read_since(...)` and `read_stream(...)` **never** raise “not found”; **return an empty iterator** if no rows.
   - They may raise `ValueError` for invalid ranges/arguments (e.g., `from_version < 1`, `to_version < from_version`).

4) **Idempotency policy (default: strict)**
   - Re-appending a previously used `event_id` **raises** `DuplicateEventIdError`.
   - If we need idempotency later, we will add an explicit `append_idempotent(...)` API in a separate ADR with precise matching rules.

5) **Timekeeping & normalization**
   - Adapters **must** return `recorded_at` as **UTC tz-aware**; they may overwrite client-provided timestamps with authoritative DB time.

## Error mapping (adapters)

| Condition                              | DB signal (examples)                                                          | Raise                   |
| -------------------------------------- | ----------------------------------------------------------------------------- | ----------------------- |
| Duplicate `event_id`                   | Unique violation on `uq_event_store_event_id`                                 | `DuplicateEventIdError` |
| Duplicate `(stream_id, version)` / gap | Unique violation on `uq_event_store_stream_id_version` or preflight gap check | `VersionConflictError`  |
| Mixed streams in a batch               | Preflight validation                                                          | `InvalidEnvelopeError`  |
| Naive/non-UTC `recorded_at`            | Preflight validation                                                          | `InvalidEnvelopeError`  |
| Non-JSON payload/metadata              | Serialization error or preflight                                              | `InvalidEnvelopeError`  |
| Connection loss / timeout              | Driver/SQLAlchemy operational errors                                          | `StoreUnavailableError` |

> **Schema notes**
>
> - Migration includes unique on `event_id` and on `(stream_id, version)`; checks enforce `version >= 1` and ULID length.
> - Indexes support global scans and per-stream reads.

## Validation rules (pre-DB)

- Single stream per batch: all envelopes must share the same `(stream_type, stream_id)`.
- `version >= 1` and **contiguous** across the batch relative to the current stream tip.
- `recorded_at` provided by client may be accepted or ignored; adapter returns UTC tz-aware.
- `payload`/`metadata` must be JSON-serializable; reserved metadata keys are allowed (`correlation_id`, `causation_id`, `actor`).
- Field length constraints must be respected (e.g., `event_id` 26 chars ULID).

## Read semantics

- `read_since(global_seq=0, …)` → global, ascending by `global_seq`; optional coarse filters (`stream_type`, `event_type`, `limit`).
- `read_stream(stream_id, from_version=1, …)` → per-stream, ascending by `version`.
- Empty results yield an empty iterator (no exception).

## Consequences

- Callers can reliably distinguish client mistakes (fix inputs) from transient store failures (retry/backoff).
- Tests can assert on precise exception types rather than DB-specific error codes.
- Adapters must implement a small mapping layer from database errors to the typed exceptions.

## Alternatives considered

- **Generic exceptions only**: simpler adapters but pushes DB specifics into callers and tests. Rejected.
- **Idempotent by default**: convenient for at-least-once publishers but requires read-before-write and strict field comparison; deferred to a future explicit API.
