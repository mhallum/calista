# ADR-0019 — Introduce `interfaces/` and `bootstrap/` Layers

**Status:** Accepted <br>
**Amends:** ADR-0018 “Adopt Hexagonal (Ports & Adapters) Package Structure”

## Context

ADR-0018 established the hexagonal package layout and high-level import boundaries. Since then, we’ve tightened a key rule—**adapters must not depend on the service layer or entrypoints**—and we want a centralized place to assemble the application (a composition root). Two gaps emerged:

- A **neutral location** for application-level interfaces/DTOs that both the service layer and adapters can depend on without violating the adapter rule or polluting the domain.
- A **bootstrap area** to wire implementations, manage lifecycle/configuration, and optionally expose small facades to entrypoints without leaking adapter details.

## Decision

Add two packages and clarify boundaries:

**`interfaces/`**
Neutral package for application-level interfaces (protocols/abstractions) and simple data carriers (DTOs) used across layers (e.g., database status provider, filestore maintenance, clocks/ID generation).
**Why:** lets adapters and the service layer meet at a shared contract **without** forcing adapters to import the service layer or pushing operational concepts into the domain. `interfaces/` remains independent (no imports from `calista.*`).

**`bootstrap/`**
Composition root responsible for wiring concrete adapters to handlers, managing lifecycle/configuration, and composing shared services (e.g., **message bus**, **unit of work**). It may expose small facades for entrypoints as needed.
**Why:** keeps entrypoints adapter-agnostic and centralizes assembly concerns that don’t belong in the service layer.

## Architecture & Dependency Rules

**Layer order (outer → inner):** `entrypoints → bootstrap → adapters → service_layer → interfaces → domain`

**Constraints (clarified):**

- `entrypoints/` depends on **`bootstrap/` only**.
- `bootstrap/` may depend on adapters, service_layer, interfaces, and domain.
- `adapters/` may depend on **`interfaces/`** and **`domain/`**; **not** on service_layer or entrypoints.
- `service_layer/` may depend on **`interfaces/`** and **`domain/`**; **not** on adapters or entrypoints.
- `interfaces/` is **independent** (no imports from `calista.*`).
- `domain/` remains innermost.

(These constraints are enforced via Import Linter contracts in `pyproject.toml`.)

## Consequences

- **Pros:** Clear seams; strict adapter rule upheld; entrypoints remain adapter-agnostic via `bootstrap/`; easier testing/substitution; composition concerns (e.g., message bus, UoW) have a home.
- **Cons:** Slightly more structure (one small extra package); import rules must remain green in CI.

## Alternatives Considered

- **Let adapters import `service_layer.ports`.** Simpler, but violates the strict adapter rule and couples adapters to application internals.
- **Put application interfaces in the domain.** Blurs ubiquitous language and pollutes the domain with operational concerns.
- **Skip `bootstrap/` and wire in entrypoints.** Leaks assembly details into UIs and weakens layering guarantees.

## Relationship to ADR-0018

This ADR **amends** ADR-0018 by introducing `interfaces/` and `bootstrap/` and by tightening import rules. ADR-0018 remains valid; this ADR clarifies where app-level contracts live and where composition happens (including common shared services like the message bus and unit of work).
