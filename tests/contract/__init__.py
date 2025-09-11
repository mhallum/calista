"""Contract tests.

Purpose
- Define behavior/invariants once and run them against multiple implementations
  (e.g., different adapters or backends) to keep them interchangeable.

Guidelines
- Parametrize implementations via fixtures.
- Assert only the public contract (inputs/outputs/effects), not internals.
- Keep environment minimal and consistent across implementations.
"""
