# ADR-0020: EventStore.append Return Semantics

**Status**: Accepted <br>
**Related**: ADR-0005 Event Store, ADR-0006 Event Envelope, ADR-0021 Event Store Error Semantics & Read Behavior

## Context

The `append()` method is the sole entry point for writing events into the store. Its contract must be precise:

- What values are filled in by the store vs honored from the caller
- In what order results are returned
- Whether returned envelopes are *copies* of input objects or re-used
- How the contract works across adapters (in-memory, SQLite, Postgres)

Without a clear return policy, service-layer code and tests become adapter-coupled, and invariants (like global sequencing) are difficult to verify.

## Decision

1. **Return persisted envelopes**
   - `append()` always returns a sequence of fully populated `EventEnvelope` objects that reflect the **state committed in the store**.
   - These include:
     - `global_seq`: assigned by the store (monotonic, unique)
     - `recorded_at`: authoritative UTC tz-aware timestamp from the store
   - Caller-supplied `global_seq` and `recorded_at` are ignored.

2. **Order preservation**
   - Returned envelopes are in the **same order as input**, regardless of how the DB assigns IDs.
   - This ensures the caller can safely zip input → output.

3. **Identity semantics**
   - Returned envelopes are **new objects** (re-hydrated from DB rows).
   - Input instances must not be mutated in place by the store.

4. **Atomicity**
   - On success: all returned envelopes have been durably written.
   - On failure: no envelopes are returned (exception is raised instead).

5. **Batch type flexibility**
   - `append()` accepts either:
     - A sequence of `EventEnvelope` instances, or
     - An `EventEnvelopeBatch` object
   - In either case, return type is always `Sequence[EventEnvelope]`.

## Consequences

- Callers can treat the return value as the *canonical source of truth* for `global_seq` and `recorded_at`.
- Tests can assert invariants (monotonic `global_seq`, increasing `version`, etc.) without adapter-specific knowledge.
- Adapters must perform a **round-trip read of inserted rows** (`INSERT … RETURNING`) to populate authoritative fields.
- Callers cannot rely on object identity: equality should be value-based (`==`), not `is`.

## Alternatives considered

- **Return nothing** (`None`): simpler API but forces caller to re-query store to see assigned fields. Rejected as inefficient and error-prone.
- **Mutate inputs in place**: avoids allocations, but creates hidden side effects and makes immutability impossible. Rejected.
- **Return only assigned fields** (e.g., a list of `(global_seq, recorded_at)` tuples): concise, but disconnects metadata from event content. Rejected.
