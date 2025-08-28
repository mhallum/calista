# ADR-0016: Adopt Mutmut for Mutation Testing (supersedes Cosmic Ray)

**Status**: Accepted <br>
**Supersedes**: ADR-0015 "Mutation Testing Policy (Cosmic Ray)

## Context

We introduced Cosmic Ray for mutation testing (ADR-0015). In practice we encountered persistent issues:

- **Maintenance risk:** upstream development is largely inactive; open issues remain unresolved for long periods.
- **Operational friction:** session DB schema churn, brittle `cr-filter-git` behavior, complex CI orchestration.
- **Developer experience:** difficulty aligning git filters, problems around type hints and annotations.

We require a simpler, actively maintained tool with predictable CI behavior and strong pytest integration.

## Decision

Adopt **Mutmut** as the project’s mutation testing tool.

- Use **file-level diff scope** for PR checks by passing changed paths with `--paths-to-mutate`.
- Run a **full nightly sweep** across `src/` with coverage guidance (`--use-coverage`).
- Publish **JUnit XML** results and maintain a **mutation badge** updated from the nightly run.
- Retain the Cosmic Ray ADR for history but mark it **Superseded**.

## Rationale

- **Simplicity:** straightforward pytest integration, no external DB.
- **Maintenance:** Mutmut is actively maintained and Python 3.13–compatible.
- **CI ergonomics:** direct commands with JUnit output; easier to scope runs.
- **Trade-offs:** lacks line-level diff filter, but file-level scope plus nightly full run is sufficient.

## Scope

- Applies to all Python code under `src/`.
- Replaces Cosmic Ray tooling, configs, and workflows.
- Adds pytest fixtures to clear global SQLAlchemy `MetaData` between tests for determinism.

## Consequences

**Positive**

- Lower CI friction, simpler config.
- Better compatibility with type-annotated code.
- Badge + nightly runs give clear visibility.

**Negative**

- Coarser PR scope (file-level vs line-level).
- Fewer mutation operators than Cosmic Ray.

Both are acceptable given stability gains.

## Alternatives Considered

- **Stay with Cosmic Ray:** rejected due to lack of maintenance and ongoing friction.
- **Disable mutation testing:** rejected; mutation testing remains valuable.
- **Custom git/line filter for Mutmut:** deferred; complexity not justified now.

## Success Metrics

- PR job runtime within ~5–10 minutes.
- Nightly full sweep ≤ 60 minutes.
- Zero or decreasing survivor trend over time.
- No recurring CI flakes attributable to the mutation tool.

## Decision Record

- **Chosen tool:** Mutmut
- **PR mode:** file-level scope via `--paths-to-mutate`
- **Nightly mode:** full project with coverage
- **Reporting:** JUnit XML + badge committed on `main`
- **Supersedes:** ADR-0015 (Cosmic Ray)
