"""CALISTA test suite.

Folder taxonomy
- unit/         : Isolated, fast checks of a single module/class/function.
- integration/  : Real interactions with external systems (DB, FS, network, etc.).
- functional/   : User-visible flows and features tested end-to-end at the boundary.
- contract/     : Shared behavior/invariants enforced across multiple implementations.
- helpers/      : Shared utilities (no tests here).

General guidance
- Keep unit fast and deterministic (no real I/O); prefer fakes over mocks at boundaries.
- Integration hits real dependencies with realistic setup/teardown.
- Functional asserts user-observable results, not internals.
- Contract parametrizes implementations to ensure consistent behavior.
- Property-based tests live with the layer they exercise and use @pytest.mark.property.
- Suggested markers: unit, integration, functional, contract, property, slow
"""
