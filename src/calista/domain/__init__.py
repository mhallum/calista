"""Domain layer for CALISTA.

Contains business rules: aggregates, value objects, domain events, and outbound
ports (interfaces) that the application depends on. This package is deliberately
technology-agnostic.

Dependency rule: do not import from `calista.adapters` or `calista.entrypoints`.
"""
