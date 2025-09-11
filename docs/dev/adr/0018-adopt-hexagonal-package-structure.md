# ADR-0018: Adopt Ports & Adapters (Hexagonal) Package Structure

**Status:** Accepted

## Context

We used both “infrastructure” and “adapters,” which caused ambiguity. The CLI lived at `calista/cli`, making an inbound adapter appear as part of the core (domain + service layer). We want clear boundaries, explicit dependency rules, and a layout that can accommodate a future browser UI.

## Decision

Adopt a Ports & Adapters (Hexagonal) package structure with four top-level areas:

- **domain/** — business rules: aggregates, value objects, domain events; may define **ports** (interfaces). _No tech deps._
- **service_layer/** — use-case orchestration/transactions; calls domain ports.
- **adapters/** (**= infrastructure**) — implementations of ports (DB, event store, filestore, HTTP), persistence mappers, schema/Alembic, envelope.
- **entrypoints/** — inbound adapters (CLI, HTTP route handlers, scheduled jobs).

**Ports placement.** Outbound ports (e.g., event store, filestore) are owned by the business and live in **`domain/ports/`** (preferred). Adapters implement them. Inbound use-case API remains in **service_layer**.

**Source tree updates.**

- `calista/infrastructure/**` → `calista/adapters/**`
- `calista/cli/**` → `calista/entrypoints/cli/**`
- Console script target: `calista = "calista.entrypoints.cli.main:calista"`
- Alembic scripts resolve under `calista.adapters.db.alembic`

**Future browser UI.** If/when we add dashboards, keep them separate from Python entrypoints (e.g., a top-level `web/` or `frontend/` with its own JS toolchain). Python HTTP handlers remain under `entrypoints/api/`.

## Dependency rules (must hold)

entrypoints  →  service_layer  →  domain
adapters     →  domain

- **Forbidden:** `domain → adapters/entrypoints`, `service_layer → entrypoints`.
- Event envelopes, ULIDs, DB timestamps, row mappers, engines, Alembic: **adapters** only.

## Testing layout (policy)

- Organize by **scope** then **layer**:
    - `tests/unit/{domain,service_layer,adapters,entrypoints/...}`
    - `tests/integration/adapters/{db,eventstore,...}`
    - `tests/functional/entrypoints/cli/`
    - Property-based tests live with the layer they exercise (e.g., `unit/adapters/filestore/`) and are marked `@pytest.mark.property`.

## Consequences

- **Pros:** clearer navigation and vocabulary; explicit boundaries; easier onboarding/review; safer imports.
- **Cons:** one-time churn in paths/imports.
- **Guardrails:** keep core (domain + service_layer) free of tech concerns and unaware of entrypoints.
