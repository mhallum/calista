"""Bootstrap (composition root) for CALISTA.

Assembles the application at runtime: wires concrete adapters to service-layer
handlers (queries/commands), composes shared services (e.g., message bus, unit
of work), reads configuration, and may expose small facades for entrypoints
(e.g., `bootstrap_queries()`).

Import rules:
- Entry points import *this* package (not adapters/service_layer/interfaces/domain).
- This package may import: `calista.adapters`, `calista.service_layer`,
  `calista.interfaces`, `calista.domain`, and `calista.config`.
- Inner layers must not import `calista.bootstrap`.

Public surface:
- Re-export composition factories from this module; keep wiring helpers internal.
- No business rules live here; this is assembly and lifecycle only.
"""
