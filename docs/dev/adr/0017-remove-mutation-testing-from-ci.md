# ADR-0017: Remove Mutation Testing from CI (Mutmut remains optional)

**Status:** Accepted <br>
**Supersedes:** ADR-0016 Adopt Mutmut for Mutation Testing (supersedes Cosmic Ray)

## Context

We previously adopted **Mutmut** (ADR-0016) to replace Cosmic Ray as our mutation testing tool, and integrated it into CI.
In practice, running mutation testing in CI introduced significant friction:

- **Performance cost:** Mutmut runs can take a long time, even when scoped to subsets of files.
- **Tooling limitations:** Mutmut ≥3.x no longer supports include-only scoping; filtering in CI became fragile.
- **Value vs. cost trade-off:** Our existing test suite, coverage gates, type checks, and property-based tests already give strong confidence. Mutation testing provided limited additional signal compared to its maintenance burden.

We want to keep mutation testing available as a developer tool, but not as a required CI step.

## Decision

- Remove **mutation testing from CI pipelines** (PR checks and main).
- Keep **Mutmut** as a development dependency in `pyproject.toml`.
- Mark ADR-0016 as **Superseded by this ADR**.

## Consequences

**Positive**

- Faster, more reliable CI (no long mutation runs, no brittle filters).
- Developers still have access to mutation testing locally.
- Lower maintenance burden.

**Negative**

- Mutation testing results are not continuously visible in CI.
- Survivors may go unnoticed unless developers run Mutmut explicitly.

## Alternatives Considered

- **Keep Mutmut in PR CI:** Rejected due to runtime and lack of include-only support.
- **Nightly automated runs:** Rejected; offers limited incremental value.
- **Abandon mutation testing entirely:** Rejected; still useful as an optional tool during release hardening.

## Decision Record

- **Remove Mutmut from CI** (blocking jobs).
- **Keep Mutmut** in dev dependencies.
- **Supersedes:** ADR-0016 (Adopt Mutmut).
