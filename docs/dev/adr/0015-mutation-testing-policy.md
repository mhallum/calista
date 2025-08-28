# ADR-0015: Mutation Testing Policy (Cosmic Ray)

**Status**: Accepted <br>
**Related**: ADR-0014 Event Store Testing Strategy

## Context

CALISTA needs stronger test quality signals than line coverage, especially for critical subsystems (event store, filestore, transforms). Mutation testing provides this but can be slow. We need a policy that balances signal quality with CI cost.

## Decision

- **Tool**: Use **Cosmic Ray** for mutation testing.
- **Config**: Maintain a single `cr.toml` shared by local dev and CI.
- **PR policy**: Run mutation tests only on PRs labeled `mutation`, restricted to lines changed vs `origin/main` (git-line filter).
- **Nightly policy**: Run a full mutation test on `main` nightly (no git-line filter).
- **Threshold (gate)**: Fail CI if **survival rate > 15%** (initial value; subject to revision).
- **Scope**: Mutate `src/`, excluding generated code (e.g., tests, migrations). Prioritize critical modules for more frequent runs.
- **Artifacts**: Publish `mutation-report.html` and `mutation.svg` as CI artifacts; do **not** commit them.
- **Ephemera**: Cosmic Ray session DBs (e.g., `*.sqlite`) are temporary and should be ignored in VCS.

## Operator Filter Policy

**Intent.** Suppress mutants that create noise without improving fault-finding power.

**Application.** Apply operator/pragma/git filters **after** `cosmic-ray init` and **before** `baseline`/`exec`.

**Initial exclusions (class & rationale).**

1. **Type-hint unions (`str | None`)** — exclude BitOr (`|`) replacements in annotations.
   _Rationale:_ These do not affect runtime behavior; mutants like `str // None` are non-actionable.
2. **Signature separators (`*`/`/`)** — do **not** exclude globally.
   _Rationale:_ Prefer contract tests enforcing keyword-only/positional-only rules. Use targeted `# pragma: no mutate` on specific signatures if needed.

**Guidelines.**

- Default to **including** operators; exclude only with a clear, documented rationale.
- Prefer **targeted pragmas** over global bans where the operator is valuable elsewhere.
- Adding/removing a **class** of exclusions is a policy change (ADR update). Narrow, non-policy tweaks may be handled in config with justification.

## CI Policy

- **PRs**: Label `mutation` to trigger; apply git-line filter; enforce survival-rate gate; upload HTML report and badge.
- **Nightly**: Full run on `main` without git-line filter; same reporting and gate.

## Alternatives Considered

- **mutmut**: simpler DX; weaker built-in CI/reporting.
- **Full mutation on every PR**: excessive runtime.
- **Two TOMLs (PR vs nightly)**: workable but risks config drift; prefer single TOML + conditional filters.

## Consequences

- PRs stay fast unless explicitly labeled.
- Nightly runs surface real test gaps.
- Some benign mutants (e.g., signature separators) require targeted tests or pragmas instead of broad operator bans.
