"""Service layer for CALISTA.

Implements application use-cases: command/query handlers, orchestration, and
transaction boundaries. Calls domain objects and outbound ports defined by the
domain.

Dependency rule: may import `calista.domain`, but not `calista.adapters` or
`calista.entrypoints`.
"""
