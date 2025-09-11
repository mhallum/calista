"""Entrypoints (inbound adapters) for CALISTA.

Expose the application to the outside world: CLI commands, HTTP routes/controllers,
and job runners. Parse and validate inputs, call service-layer handlers, and present
results.

Dependency rule: may import `calista.service_layer`; avoid importing
`calista.adapters` directly.
"""
