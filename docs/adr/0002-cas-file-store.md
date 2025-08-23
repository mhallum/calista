# ADR-0007: Content-Addressed File Store (CAS)

**Status**: Accepted

## Context

CALISTA must store user artifacts immutably with strong provenance. We want:

- A byte store where identity is the **content digest** (e.g., `sha256:<hex>`).
- Simple, testable semantics for writing/reading blobs across backends (local FS, object stores, memory).
- Clear separation between **content identity** and **human/path aliases**.

Historically, coupling path rules into the store complicates atomicity, recovery, and audits.

## Decision

Adopt a **pure CAS** file store with the following interface and semantics:

- **Identity**: Blobs are addressed only by `digest` (`"<algorithm>:<hex>"`, lowercase).
- **Writes**:
  - `open_write(fsync: bool = True) -> Writer` returns a staging handle.
  - `Writer.write(bytes)` appends to a temp object.
  - `Writer.commit(expected_digest: str | None) -> BlobStat` finalizes the blob.
  - **Idempotency**: `commit()` **SHOULD** be idempotent—if the digest already exists, discard staged data and return the existing blob’s `BlobStat`.
  - **Leak safety**: Exiting a writer context without `commit()` **MUST** discard staged data (`abort()`) and close resources.
- **Reads**:
  - `open_read(digest) -> BinaryIO` returns a caller-closed stream.
  - `stat(digest) -> BlobStat` returns cheap metadata (MUST NOT read the body; `size` MAY be `None` if expensive).
- **Conveniences** (non-abstract helpers):
  - `exists(digest) -> bool`
  - `put_path(path, ...) -> BlobStat`
  - `put_bytes(data, ...) -> BlobStat`
  - `put_stream(stream, ...) -> BlobStat`
  - `readall(digest) -> bytes`
- **Durability**:
  - When `fsync=True`, implementations **SHOULD** durably install the blob on commit (e.g., `fsync` file and parent dir on POSIX).
  - Placement **SHOULD** be atomic (temp + `os.replace` or equivalent).
- **Error taxonomy** (module-scoped exceptions):
  - `FileStoreError` (base), `NotFound`, `ReadOnlyError`, `IntegrityError`.

> **Algorithm:** The canonical and only supported digest algorithm is **SHA-256**. All digests are formatted sha256:<hex> (lowercase). Changing the canonical algorithm would require a separate ADR and a migration plan.

> **Aliases/paths are out of scope here.** Any mapping of `(namespace, relpath) → digest` is handled outside the CAS as a DB-backed **projection**; details are deferred to future ADR if needed.

## Rationale

- **Separation of concerns**: CAS remains verifiable and minimal; aliasing is a rebuildable read model.
- **Recoverability**: If alias state is lost/corrupt, we can replay events and rescan the CAS.
- **Determinism & dedup**: Content identity prevents accidental duplication and simplifies audits/GC.
- **Portability**: A thin interface makes alternative backends straightforward.

## Consequences

- Callers ingest bytes once to get a `digest`, then persist only the digest in domain state/events.
- Any user-facing or workflow paths are **derived** via a projection (separate ADR).
- Backends must implement safe staging, atomic installs, and cheap `stat()`.

## Alternatives Considered

- **Path-addressed store** (no CAS): simpler ergonomics; loses dedup/provenance. _Rejected._
- **CAS with built-in aliases**: convenient but couples identity to paths and complicates atomicity/rollbacks. _Rejected._
- **Mandate DataLad/fsspec now**: useful later; adds complexity and constraints today. _Deferred integration._

## Implementation Notes

- Digest format: `"<algorithm>:<hex>"` (lowercase algorithm & hex). Future multi-algorithm support may add negotiation/migration.
- `BlobStat = { digest, size?, uri? }`; `uri` is a **hint** (e.g., `file:///…`), never identity.
- Writers: `commit()` and `abort()` **MUST** be idempotent; `abort()` **MUST** be a no-op after a successful `commit()`.

## Testing

- Writer lifecycle: write/commit/abort/context-exit (no leaks; temps cleaned).
- Duplicate ingest returns the same digest and does not rewrite bytes.
- `stat()` never reads blob bodies; remote backends map to HEAD/metadata calls.
- Durability hint honored where the platform permits.
