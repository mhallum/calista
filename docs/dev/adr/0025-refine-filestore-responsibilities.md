# ADR-0025: Refine Filestore Responsibilities — Remove `put` and `export`

**Status:** Accepted
**Supersedes:** ADR-0024 (revised)

## Context

ADR-0024 defined a simplified CAS filestore but still included two operations that reach outside the CAS boundary:

* **`put`** (store from a filesystem path)
* **`export`** (copy a blob to an arbitrary filesystem path)

Both operations involve interacting with the user’s filesystem. That behavior belongs in ingestion and workflow services, not in a low-level CAS component whose job is simply: “store blobs by content and read them back.”

## Decision

The `FileStore` interface is reduced to the minimal CAS operations:

* `store(stream)` — read bytes from a binary stream, hash them, and install the blob.
* `open_read(sha256)`
* `exists(sha256)`

The filestore no longer performs path-based ingestion or export. Those responsibilities move to higher-level services where policies about user filesystem access actually belong.

## Rationale

* **Clearer boundaries.**
  Ingestion and export are workflow-specific and belong elsewhere.

* **Safer by construction.**
  Restricting the filestore to streams guarantees it can’t accidentally write outside its root.

* **Simpler implementations and tests.**
  Backends only handle CAS semantics. Contract tests remain small and precise.

## Consequences

* Callers must handle reading external files themselves, then pass the resulting stream into `store()`.
* Export utilities (if needed) live in a higher layer such as:

    * CLI helpers,
    * ingestion/export services,
    * or workflow-specific adapters.
* Existing backends shrink; only pure CAS behavior remains.
* Contract tests focus strictly on content-addressable guarantees.

## Alternatives Considered

* **Keep `put` and `export`**
  Rejected — it reintroduces filesystem concerns into a CAS component.
* **Make them optional helpers**
  Rejected — still muddies the abstraction boundary.
