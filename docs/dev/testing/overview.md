# Testing Overview

This page describes how CALISTA configures and runs tests with pytest: where configuration lives, how the test suite is organized, which markers we use, and how to select tests efficiently.

## Pytest Configuration

All pytest options are defined in `pyproject.toml` under the `[tool.pytest.ini_options]` section.
We deliberately avoid `pytest.ini`, `tox.ini`, or `setup.cfg`, since their presence takes precedence and would cause pytest to ignore the `pyproject.toml` block.
Keeping all configuration in `pyproject.toml` ensures tool settings are centralized, Git-tracked, and consistent with the rest of the project (ruff, mypy, etc.).

## Test Suite Organization

- `unit/`
  Isolated, fast checks of a single module/class/function. No real I/O. Prefer fakes over mocks at boundaries. Deterministic assertions.

- `integration/`
  Real interactions with external systems (database, filestore, network). Use realistic setup/teardown; minimize mocking.

- `functional/`
  User-visible flows at the system boundary (e.g., CLI via `click.CliRunner`). Treat the system as a black box; assert outputs/side-effects, not internals.

- `contract/`
  Shared behavior/invariants enforced across multiple implementations/backends. Parametrize implementations via fixtures. Assert the public contract only.

- `helpers/`
  Shared utilities for tests (matchers, builders, small helpers). **No tests live here.**

- Property-based tests
  Live alongside the layer they exercise and opt-in with `@pytest.mark.property`.

## Testing & Markers

CALISTA uses a small, stable set of **pytest markers**. Base suite marks are applied by **folder** during collection; cross-cutting marks are **opt-in**.

### Marker taxonomy

| Marker        | Meaning                                                                | Default application (by folder) |
| ------------- | ---------------------------------------------------------------------- | ------------------------------- |
| `unit`        | Fast, isolated checks of a single module/class/function (no real I/O). | `tests/unit/`                   |
| `integration` | Interactions with external systems (DB, filestore, network, etc.).     | `tests/integration/`            |
| `functional`  | User-visible flows at the boundary (e.g., CLI via `CliRunner`).        | `tests/functional/`             |
| `contract`    | Invariants shared across implementations/backends.                     | `tests/contract/`               |
| `property`    | Property-based style (Hypothesis or similar).                          | **Opt-in** per module/test      |
| `slow`        | Slow tests                                                             | **Opt-in** per module/test      |

### Selection recipes

```bash
# Fast local cycle (pure unit, exclude slow)
pytest -m "unit and not slow"

# Everything except slow
pytest -m "not slow"

# Only integration
pytest -m integration

# Functional OR contract
pytest -m "functional or contract"

# All property-based tests (across suites)
pytest -m property
```

### Applying marks

- Base suite marks (`unit`, `integration`, `functional`, `contract`) are added **by folder** during collection; no manual tagging needed.
- Cross-cutting marks (`property`, `slow`) are **opt-in** at module scope (e.g., `pytestmark = [pytest.mark.slow]`).

### Registration

```toml
[tool.pytest.ini_options]
markers = [
  "unit: Unit tests (fast, isolated, no real I/O)",
  "integration: Integration tests (real external systems)",
  "functional: Functional tests at the boundary (CLI/API flows)",
  "contract: Contract/invariant tests across implementations",
  "property: Property-based tests",
  "slow: Slow tests"
]
```

### Consistency rules

- Put tests where they **conceptually** belong; the folder will auto-apply the base mark.
- If a test needs real I/O, **move it** to `tests/integration/` rather than keeping it in `unit/`.
- Keep the marker set **small and stable**; add new marks only when they carry durable meaning.

### Integration prerequisites

- **Docker** is installed and running (Docker Desktop, Colima, Rancher Desktop, or Podman with a Docker-compatible socket).
- No environment variables are required to run tests; **Testcontainers** will provision Postgres automatically.
- Ensure the machine can pull container images (network access).

### CI usage

- **Pull requests:** run the **entire suite**, including tests marked `slow`.
- **Future adjustment (not active):** if the number of `slow` tests grows significantly, we may switch PRs to `-m "not slow"` and run `slow` in scheduled jobs.

## Further reading

- [Event Store Testing](eventstore.md)
