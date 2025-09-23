"""Support namespace for cross-cutting, dependency-light helpers.

This package provides a neutral location for small, reusable functions that
would otherwise clutter feature packages. It is not a new architectural layer.

Scope (ADR-0023):
- Small, stateless helpers with minimal dependencies (e.g., sanitizing strings/URLs,
  path utilities, trivial env parsing, slugification).
- No business rules, no orchestration, no engines/handlers, no wiring.
- Prefer pure functions; if I/O is unavoidable (e.g., reading an environment
  variable), keep it shallow, opt-in, and easy to stub in tests.
- Organize by single-purpose modules (e.g., ``sanitize.py``, ``paths.py``,
  ``env.py``, ``slugify.py``) rather than one catch-all file.

Import direction:
- May be imported by any CALISTA package.
- Must not import from application packages. Keep dependencies to the standard library
  and only small, justified third-party utilities.

Testing & usage:
- Keep helpers deterministic and well-documented with focused unit tests.
- Treat helpers as implementation details, not public API. If a helper starts
  accumulating policy or coordination logic, promote it to a proper package.

Public API:
- Nothing is re-exported at the package level by default. Import specific
  helpers from their defining modules to avoid incidental coupling.
"""
