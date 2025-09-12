# Layered Architecture

This page explains CALISTA’s layers, what belongs in each, and the import rules enforced in CI. It complements ADR-0018 (Hexagonal structure) and ADR-0019 (Interfaces + Bootstrap).

`entrypoints → bootstrap → adapters → service_layer → interfaces → domain`

## Principles

- Depend **inward only** (outer layers may import inner layers; never the reverse).
- **Adapters must not depend on service_layer or entrypoints.**
- `interfaces/` is **independent** (no imports from `calista.*`).
- Only **bootstrap** reads `calista.config` and injects values.

## Responsibilities by layer

- **entrypoints/** — CLI/UI. Talks only to **bootstrap**. No direct imports from adapters/service_layer/interfaces/domain.
- **bootstrap/** — Composition root. Wires adapters to handlers, composes shared services (e.g., message bus, unit of work), reads config, may expose small facades.
- **adapters/** — Concrete infrastructure. Implement **interfaces** (and, where applicable, domain repositories). Never import service_layer or entrypoints.
- **service_layer/** — Application logic: commands/queries/handlers. Depends on **interfaces** and **domain** only.
- **interfaces/** — Neutral contracts: protocols/ABCs and small DTOs shared by service_layer and adapters. No imports from `calista.*`.
- **domain/** — Entities, domain services, domain repositories/ports. No imports from other app packages.

## Import rules (matrix)

Depend inward only; Import Linter enforces the following matrix.

| From \ To         | entrypoints | bootstrap | adapters | service_layer | interfaces | domain |
| ----------------- | :---------: | :-------: | :------: | :-----------: | :--------: | :----: |
| **entrypoints**   |      —      |     ✅     |    ❌     |       ❌       |     ❌      |   ❌    |
| **bootstrap**     |      ❌      |     —     |    ✅     |       ✅       |     ✅      |   ✅    |
| **adapters**      |      ❌      |     ❌     |    —     |       ❌       |     ✅      |   ✅    |
| **service_layer** |      ❌      |     ❌     |    ❌     |       —       |     ✅      |   ✅    |
| **interfaces**    |      ❌      |     ❌     |    ❌     |       ❌       |     —      |   ❌    |
| **domain**        |      ❌      |     ❌     |    ❌     |       ❌       |     ❌      |   —    |

*Notes:*

- If you need **type-only** names from `interfaces` in entrypoints, prefer documenting them in `bootstrap` or guard imports with `typing.TYPE_CHECKING`; keep the runtime rule as ❌.

## References

- ADR-0018 — Adopt Hexagonal (Ports & Adapters) Package Structure
- ADR-0019 — Introduce `interfaces/` and `bootstrap/` Layers
