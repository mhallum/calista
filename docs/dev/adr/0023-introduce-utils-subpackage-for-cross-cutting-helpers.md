# ADR-0023: Introduce `calista.utils` for Cross-Cutting, Dependency-Light Helpers

**Status:** Accepted <br>
**Related:** ADR-0018 Hexagonal Package Structure, ADR-0019 Interfaces & Bootstrap, ADR-0022 Logging

## Context

A need arose to reuse sanitization helpers (e.g., redacting messages/exceptions and rendering credential-safe database URLs) from the logging package. An early sanitizer already lived under the CLI layer (`calista/cli/helpers`), tying a cross-cutting concern to a UI package and complicating reuse. This highlighted the absence of a neutral place for small utilities that are not specific to CLI, logging, or any other feature package.

## Decision

Create `calista.utils` as a **support namespace** (not a new architectural layer) for cross-cutting, dependency-light helpers.

- **Import direction:** Any package may import `calista.utils`. The `calista.utils` package must not import CLI, logging, services/domain, or adapters.
- **Scope:** Small, stateless helpers that are broadly useful (e.g., sanitization/redaction, env parsing, slugification, simple path/string utilities). No wiring, handlers, engines, or business logic.
- **Organization:** Prefer single-purpose modules over a catch-all file (e.g., `sanitize.py`, `env.py`, `slugify.py`, `paths.py`).

## Consequences

### Positive

- Provides a neutral home for cross-cutting helpers, improving reuse and consistency across packages.
- Preserves architectural boundaries by keeping utilities “leaf-only” in the dependency graph.
- Keeps feature packages (CLI, logging, adapters, services) focused on their primary concerns.

### Risks / Mitigations

- *Risk:* “Junk drawer” growth.
  *Mitigation:* Single-purpose modules, narrow scope, and adherence to the import-direction rule.

## Alternatives Considered

- **Keep utilities in CLI helpers:** Encourages UI-centric dependencies and hinders reuse outside CLI.
- **Keep utilities in logging:** Mixes generic utilities with handler/formatter concerns and limits applicability elsewhere.
- **No shared namespace:** Leads to duplication and inconsistent behavior across packages.
