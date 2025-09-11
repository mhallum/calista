"""Adapters (infrastructure) for CALISTA.

Provide concrete implementations of domain ports (e.g., databases, event store,
filestore, HTTP clients), plus persistence mapping and related wiring (engines,
metadata, migrations).

Dependency rule: may import `calista.domain`; the domain must not import this
package.
"""
