# ADR-0024: Simplified Content-Addressed FileStore

**Status**: Accepted
**Supersedes**: ADR-0002 “Content-Addressed File Store (CAS)”

## Context

CALISTA must store user artifacts immutably with strong provenance. We want:

* A content-addressed byte store where identity is the **content digest**.
* A minimal, stable interface that multiple backends can implement (local filesystem, fake/in-memory, future remote/object stores).
* Clear separation between **content identity** and any higher-level aliasing or filesystem paths.

The earlier filestore design (ADR-0002) introduced a writer/commit API, prefixed digests (for example, `"sha256:<hex>"`), explicit durability controls, and a more complex lifecycle. In practice this was more machinery than the system needed, and no implementation was ever built against that ADR.

A simplified model is both easier to implement and easier to test.

---

## Decision

We adopt a **simplified CAS filestore interface** based on raw SHA-256 hex digests and a small, backend-portable API.

### Identity

* Blobs are identified by a **raw SHA-256 hexadecimal string**, consisting of 64 lowercase hex characters.
* The digest algorithm is fixed and implicit; no textual prefix such as `"sha256:"` is used.
* Call-sites persist and reference only this hex digest as the blob identifier.

### Interface

The filestore interface consists of:

* A small value object representing blob metadata, containing at least:

    * The size of the blob in bytes.
    * The blob’s SHA-256 digest (the 64-character hex string).

* A `FileStore` abstraction that provides exactly these operations:

    * **Store by path**: copy a file from a filesystem path into the filestore, returning the blob’s metadata (including size and digest).
    * **Store from a stream**: read from a binary file-like object (from its current position to end-of-file), store the bytes in the filestore, and return the blob’s metadata.
    * **Open for reading**: open a blob identified by its digest as a read-only binary stream.
    * **Export**: copy a blob identified by its digest to an arbitrary filesystem path, with an option to control whether an existing file may be overwritten.
    * **Existence check**: check whether a blob with a given digest is present in the filestore.

### Backend expectations

* Implementations **must** provide atomic installation of blobs and deduplication based on the digest.
* Implementations **must** validate that supplied digests are well-formed SHA-256 hex strings.
* Implementations **may** use a sharded on-disk layout (for example, splitting the digest into subdirectories) or any equivalent layout appropriate for the backend.
* Higher-level aliasing or path projections are explicitly out of scope for the filestore and belong in separate components.

---

## Rationale

* The simplified API matches what call-sites actually need: ingest bytes, obtain a digest and size, read or export blobs, and perform simple existence checks.
* Fixing the digest algorithm reduces noise and avoids prefix handling throughout the codebase.
* Eliminating the writer/commit lifecycle and explicit durability flags simplifies testing and lowers implementation and maintenance cost.
* CAS semantics—deduplication, content-addressable identity, and provenance—are preserved.
* A small, stable interface enables reliable contract tests that can run against any backend implementation.

## Consequences

* Domain code and events store raw SHA-256 hex digests as the canonical identifiers for stored blobs.
* Any mapping from human-meaningful paths, namespaces, or workflow-specific locations to digests is handled elsewhere (for example, by database-backed projections) and not within the filestore itself.
* Future filestore backends (local, fake, or remote) must conform to this interface and will be validated using a shared contract-test suite.

## Alternatives Considered

* **Retain the writer/commit API from ADR-0002**
  This pattern can be useful for some remote or object-store backends, but it introduced lifecycle complexity not required for current needs. It was rejected in favor of a smaller, simpler interface. A writer-style API could be reintroduced later as an optional extension if warranted.

* **Retain prefixed digest strings such as `"sha256:<hex>"`**
  Making the algorithm explicit in the identifier is not necessary while only one algorithm is supported. Prefixes add parsing and validation overhead without practical benefit. Raw hex identifiers are sufficient for the current design.

* **Fold alias/path management into the filestore**
  Combining naming and storage would couple identity to paths, complicate atomicity and rollback, and make projections harder to rebuild. Keeping aliasing separate maintains clearer responsibilities and better recoverability.
